"""Main processing pipeline for Flou2Flow.

Implements a 4-step chain-of-thought pipeline:
1. Context Understanding → Summarize & identify domain
2. Entity Extraction → Extract actors, tasks, decisions, rules
3. Flow Construction → Build directed process graph
4. Workflow Generation → Generate Elsa-compatible JSON + Mermaid diagram
"""

from __future__ import annotations

import json
import logging

from .llm import llm_client
from .models import (
    Actor,
    BusinessRule,
    Condition,
    DataObject,
    Decision,
    FlowConnection,
    ParallelBranch,
    PipelineResult,
    ProcessContext,
    ProcessEntities,
    ProcessFlow,
    Task,
)
from .prompts import (
    CONTEXT_SYSTEM_PROMPT,
    CONTEXT_USER_PROMPT,
    ENTITIES_SYSTEM_PROMPT,
    ENTITIES_USER_PROMPT,
    FLOW_SYSTEM_PROMPT,
    FLOW_USER_PROMPT,
)
from .exporters import generate_elsa_workflow, generate_mermaid_diagram

logger = logging.getLogger(__name__)


async def run_pipeline(input_text: str) -> PipelineResult:
    """Run the full Flou2Flow pipeline on unstructured input text.

    Args:
        input_text: Unstructured business process description.

    Returns:
        PipelineResult with all intermediate and final results.
    """
    result = PipelineResult()

    # ── Step 1: Context Understanding ──────────────────────────────────
    try:
        logger.info("Step 1: Context Understanding")
        context = await step_context_understanding(input_text)
        result.context = context
        result.steps_completed.append("context_understanding")
        logger.info(f"Context extracted: domain={context.domain}, stakeholders={len(context.stakeholders)}")
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        result.errors.append(f"Context understanding failed: {str(e)}")
        return result

    # ── Step 2: Entity Extraction ──────────────────────────────────────
    try:
        logger.info("Step 2: Entity Extraction")
        entities = await step_entity_extraction(input_text, context)
        result.entities = entities
        result.steps_completed.append("entity_extraction")
        logger.info(
            f"Entities extracted: actors={len(entities.actors)}, "
            f"tasks={len(entities.tasks)}, decisions={len(entities.decisions)}"
        )
    except Exception as e:
        logger.error(f"Step 2 failed: {e}")
        result.errors.append(f"Entity extraction failed: {str(e)}")
        return result

    # ── Step 3: Flow Construction ──────────────────────────────────────
    try:
        logger.info("Step 3: Flow Construction")
        flow = await step_flow_construction(context, entities)
        result.flow = flow
        result.steps_completed.append("flow_construction")
        logger.info(f"Flow constructed: connections={len(flow.connections)}")
    except Exception as e:
        logger.error(f"Step 3 failed: {e}")
        result.errors.append(f"Flow construction failed: {str(e)}")
        return result

    # ── Step 4: Workflow Generation ────────────────────────────────────
    try:
        logger.info("Step 4: Workflow Generation")
        elsa_wf = generate_elsa_workflow(context, entities, flow)
        result.elsa_workflow = elsa_wf
        mermaid = generate_mermaid_diagram(entities, flow)
        result.mermaid_diagram = mermaid
        result.steps_completed.append("workflow_generation")
        logger.info("Workflow generation complete")
    except Exception as e:
        logger.error(f"Step 4 failed: {e}")
        result.errors.append(f"Workflow generation failed: {str(e)}")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Individual Pipeline Steps
# ═══════════════════════════════════════════════════════════════════════════


async def step_context_understanding(input_text: str) -> ProcessContext:
    """Step 1: Understand the context of the business process."""
    user_prompt = CONTEXT_USER_PROMPT.format(input_text=input_text)

    response = await llm_client.chat(
        system_prompt=CONTEXT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    data = llm_client.parse_json_response(response)

    return ProcessContext(
        summary=data.get("summary", ""),
        domain=data.get("domain", ""),
        objective=data.get("objective", ""),
        stakeholders=data.get("stakeholders", []),
        language=data.get("language", "fr"),
    )


async def step_entity_extraction(
    input_text: str,
    context: ProcessContext,
) -> ProcessEntities:
    """Step 2: Extract process entities (actors, tasks, decisions, etc.)."""
    user_prompt = ENTITIES_USER_PROMPT.format(
        domain=context.domain,
        objective=context.objective,
        summary=context.summary,
        input_text=input_text,
    )

    response = await llm_client.chat(
        system_prompt=ENTITIES_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    data = llm_client.parse_json_response(response)

    # Parse actors
    actors = [Actor(**a) for a in data.get("actors", [])]

    # Parse tasks
    tasks = [Task(**t) for t in data.get("tasks", [])]

    # Parse decisions with conditions
    decisions = []
    for d in data.get("decisions", []):
        conditions = [Condition(**c) for c in d.get("conditions", [])]
        decisions.append(Decision(
            id=d["id"],
            question=d["question"],
            conditions=conditions,
        ))

    # Parse data objects
    data_objects = [DataObject(**do) for do in data.get("data_objects", [])]

    # Parse business rules
    rules = [BusinessRule(**r) for r in data.get("business_rules", [])]

    return ProcessEntities(
        actors=actors,
        tasks=tasks,
        decisions=decisions,
        data_objects=data_objects,
        business_rules=rules,
    )


async def step_flow_construction(
    context: ProcessContext,
    entities: ProcessEntities,
) -> ProcessFlow:
    """Step 3: Construct the process flow from extracted entities."""
    # Prepare task and decision summaries for the prompt
    tasks_json = json.dumps(
        [{"id": t.id, "name": t.name, "actor": t.actor_id} for t in entities.tasks],
        ensure_ascii=False,
        indent=2,
    )
    decisions_json = json.dumps(
        [
            {
                "id": d.id,
                "question": d.question,
                "conditions": [{"label": c.label, "target_id": c.target_id} for c in d.conditions],
            }
            for d in entities.decisions
        ],
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = FLOW_USER_PROMPT.format(
        summary=context.summary,
        tasks_json=tasks_json,
        decisions_json=decisions_json,
    )

    response = await llm_client.chat(
        system_prompt=FLOW_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    data = llm_client.parse_json_response(response)

    # Parse connections
    connections = [
        FlowConnection(
            from_id=c["from_id"],
            to_id=c["to_id"],
            condition=c.get("condition", ""),
        )
        for c in data.get("connections", [])
    ]

    # Parse parallel branches
    parallel = [
        ParallelBranch(
            fork_after=p["fork_after"],
            branches=p.get("branches", []),
            join_before=p.get("join_before", ""),
        )
        for p in data.get("parallel_branches", [])
    ]

    return ProcessFlow(
        start_event=data.get("start_event", ""),
        end_events=data.get("end_events", []),
        connections=connections,
        parallel_branches=parallel,
    )

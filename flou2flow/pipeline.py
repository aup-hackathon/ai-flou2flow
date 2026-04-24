"""Main processing pipeline for Flou2Flow.

Implements a 4-step chain-of-thought pipeline:
1. Context Understanding → Summarize & identify domain
2. Entity Extraction → Extract actors, tasks, decisions, rules
3. Flow Construction → Build directed process graph
4. Workflow Generation → Generate Elsa-compatible JSON
"""

from __future__ import annotations

import json
import logging
import traceback

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
from .exporters import generate_elsa_workflow

logger = logging.getLogger(__name__)


async def run_pipeline(input_text: str, model: str | None = None) -> PipelineResult:
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
        context = await step_context_understanding(input_text, model=model)
        result.context = context
        result.steps_completed.append("context_understanding")
        logger.info(f"Context extracted: domain={context.domain}, stakeholders={len(context.stakeholders)}")
    except Exception as e:
        logger.error(f"Step 1 failed: {e}")
        logger.error(traceback.format_exc())
        result.errors.append(f"Context understanding failed: {str(e) or repr(e)}")
        return result

    # ── Step 2: Entity Extraction ──────────────────────────────────────
    try:
        logger.info("Step 2: Entity Extraction")
        entities = await step_entity_extraction(input_text, context, model=model)
        result.entities = entities
        result.steps_completed.append("entity_extraction")
        logger.info(
            f"Entities extracted: actors={len(entities.actors)}, "
            f"tasks={len(entities.tasks)}, decisions={len(entities.decisions)}"
        )
    except Exception as e:
        logger.error(f"Step 2 failed: {e}")
        logger.error(traceback.format_exc())
        result.errors.append(f"Entity extraction failed: {str(e) or repr(e)}")
        return result

    # ── Step 3: Flow Construction ──────────────────────────────────────
    try:
        logger.info("Step 3: Flow Construction")
        flow = await step_flow_construction(context, entities, model=model)
        result.flow = flow
        result.steps_completed.append("flow_construction")
        logger.info(f"Flow constructed: connections={len(flow.connections)}")
    except Exception as e:
        logger.error(f"Step 3 failed: {e}")
        logger.error(traceback.format_exc())
        result.errors.append(f"Flow construction failed: {str(e) or repr(e)}")
        return result

    # ── Step 4: Workflow Generation ────────────────────────────────────
    try:
        logger.info("Step 4: Workflow Generation")
        elsa_wf = generate_elsa_workflow(context, entities, flow)
        result.elsa_workflow = elsa_wf
        result.steps_completed.append("workflow_generation")
        logger.info("Workflow generation complete")
    except Exception as e:
        logger.error(f"Step 4 failed: {e}")
        result.errors.append(f"Workflow generation failed: {str(e)}")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# Individual Pipeline Steps
# ═══════════════════════════════════════════════════════════════════════════


async def step_context_understanding(input_text: str, model: str | None = None) -> ProcessContext:
    """Step 1: Understand the context of the business process."""
    user_prompt = CONTEXT_USER_PROMPT.format(input_text=input_text)

    response = await llm_client.chat(
        system_prompt=CONTEXT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
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
    model: str | None = None,
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
        model=model,
    )

    data = llm_client.parse_json_response(response)

    # Parse actors
    actors = []
    for a in data.get("actors", []):
        if "id" in a and "name" in a:
            actors.append(Actor(**a))

    # Parse tasks - handle potential mix-ups from small models
    tasks = []
    for t in data.get("tasks", []):
        # Only parse as Task if it has a 'name' (Decisions have 'question')
        if "name" in t and "id" in t:
            tasks.append(Task(**t))
        elif "question" in t and "id" in t:
            # Mistakenly placed in tasks list
            conditions = [Condition(**c) for c in t.get("conditions", [])]
            data.setdefault("decisions", []).append(t)

    # Parse decisions with conditions
    decisions = []
    # Use a set to avoid duplicates if we moved them from tasks
    seen_decision_ids = set()
    
    for d in data.get("decisions", []):
        if "id" in d and d["id"] not in seen_decision_ids:
            if "question" in d:
                conditions = [Condition(**c) for c in d.get("conditions", [])]
                decisions.append(Decision(
                    id=d["id"],
                    question=d["question"],
                    conditions=conditions,
                ))
                seen_decision_ids.add(d["id"])
            elif "name" in d:
                # Mistakenly placed in decisions list
                tasks.append(Task(**d))

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
    model: str | None = None,
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
        model=model,
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

    # Parse parallel branches - handle flat lists from small models
    parallel = []
    for p in data.get("parallel_branches", []):
        fork_after = p.get("fork_after", "")
        join_before = p.get("join_before", "")
        
        raw_branches = p.get("branches", [])
        clean_branches = []
        
        for b in raw_branches:
            if isinstance(b, list):
                clean_branches.append(b)
            elif isinstance(b, str):
                # Small model provided a flat list of IDs
                clean_branches.append([b])
        
        if fork_after:
            parallel.append(ParallelBranch(
                fork_after=fork_after,
                branches=clean_branches,
                join_before=join_before,
            ))

    return ProcessFlow(
        start_event=data.get("start_event", ""),
        end_events=data.get("end_events", []),
        connections=connections,
        parallel_branches=parallel,
    )

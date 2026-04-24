"""Export workflow data to Elsa Workflows JSON format and Mermaid diagrams."""

from __future__ import annotations

import uuid
from typing import Any

from .models import ProcessContext, ProcessEntities, ProcessFlow


def generate_elsa_workflow(
    context: ProcessContext,
    entities: ProcessEntities,
    flow: ProcessFlow,
) -> dict[str, Any]:
    """Generate an Elsa Workflows v3 compatible JSON definition.

    Elsa Workflows uses a JSON-based format with:
    - Root activity (Flowchart or Sequence)
    - Activities (tasks, decisions, start/end events)
    - Connections between activities
    - Variables
    """
    workflow_id = str(uuid.uuid4())
    definition_id = f"flou2flow-{str(uuid.uuid4())[:8]}"

    # Build activities list
    activities = []

    # Start event
    start_activity = {
        "id": "start",
        "type": "Elsa.Start",
        "metadata": {
            "displayName": "Début du processus",
            "description": f"Start: {context.objective}",
        },
    }
    activities.append(start_activity)

    # Task activities
    for task in entities.tasks:
        actor = next((a for a in entities.actors if a.id == task.actor_id), None)
        actor_name = actor.name if actor else "Unknown"

        activity_type = {
            "human": "Elsa.UserTask",
            "system": "Elsa.RunTask",
            "manual": "Elsa.ManualTask",
        }.get(task.type, "Elsa.UserTask")

        activity = {
            "id": task.id,
            "type": activity_type,
            "metadata": {
                "displayName": task.name,
                "description": task.description,
                "actor": actor_name,
                "taskType": task.type,
            },
            "properties": {
                "taskName": {"expression": {"type": "Literal", "value": task.name}},
                "assignedTo": {"expression": {"type": "Literal", "value": actor_name}},
            },
        }
        activities.append(activity)

    # Decision activities (If/Switch)
    for decision in entities.decisions:
        activity = {
            "id": decision.id,
            "type": "Elsa.FlowDecision",
            "metadata": {
                "displayName": decision.question,
                "description": f"Decision: {decision.question}",
            },
            "properties": {
                "condition": {
                    "expression": {"type": "Literal", "value": decision.question}
                },
            },
            "outcomes": [c.label for c in decision.conditions],
        }
        activities.append(activity)

    # End event
    end_activity = {
        "id": "end",
        "type": "Elsa.End",
        "metadata": {
            "displayName": "Fin du processus",
            "description": "Process completed",
        },
    }
    activities.append(end_activity)

    # Build connections
    connections = []

    # Connect start to first element
    if flow.start_event:
        connections.append({
            "source": {"activity": "start", "port": "Done"},
            "target": {"activity": flow.start_event, "port": "In"},
        })

    # Flow connections
    for conn in flow.connections:
        connection = {
            "source": {
                "activity": conn.from_id,
                "port": conn.condition if conn.condition else "Done",
            },
            "target": {"activity": conn.to_id, "port": "In"},
        }
        connections.append(connection)

    # Connect end events
    for end_id in flow.end_events:
        connections.append({
            "source": {"activity": end_id, "port": "Done"},
            "target": {"activity": "end", "port": "In"},
        })

    # Build variables from data objects
    variables = []
    for data_obj in entities.data_objects:
        variables.append({
            "id": data_obj.id,
            "name": data_obj.name,
            "type": "Object",
            "value": "",
            "storageDriverType": "Workflow",
        })

    # Assemble the full workflow definition
    workflow = {
        "id": workflow_id,
        "definitionId": definition_id,
        "name": context.summary[:60] if context.summary else "Generated Workflow",
        "description": context.objective,
        "version": 1,
        "isLatest": True,
        "isPublished": False,
        "metadata": {
            "domain": context.domain,
            "generatedBy": "Flou2Flow",
            "stakeholders": context.stakeholders,
        },
        "root": {
            "type": "Elsa.Flowchart",
            "activities": activities,
            "connections": connections,
        },
        "variables": variables,
    }

    return workflow


def generate_mermaid_diagram(
    entities: ProcessEntities,
    flow: ProcessFlow,
) -> str:
    """Generate a Mermaid flowchart diagram from the process flow.

    Returns a Mermaid diagram string that can be rendered in the frontend.
    """
    lines = ["graph TD"]

    # Style definitions
    lines.append("    classDef startEnd fill:#10b981,stroke:#059669,color:#fff,stroke-width:2px")
    lines.append("    classDef task fill:#6366f1,stroke:#4f46e5,color:#fff,stroke-width:2px")
    lines.append("    classDef decision fill:#f59e0b,stroke:#d97706,color:#fff,stroke-width:2px")
    lines.append("    classDef humanTask fill:#8b5cf6,stroke:#7c3aed,color:#fff,stroke-width:2px")
    lines.append("    classDef systemTask fill:#06b6d4,stroke:#0891b2,color:#fff,stroke-width:2px")
    lines.append("")

    # Start node
    lines.append('    START(("🚀 Début")):::startEnd')

    # Task nodes
    for task in entities.tasks:
        # Escape special characters for Mermaid
        name = _mermaid_escape(task.name)
        actor = ""
        if task.actor_id:
            actor_obj = next((a for a in entities.actors if a.id == task.actor_id), None)
            if actor_obj:
                actor = f"<br/><small>👤 {_mermaid_escape(actor_obj.name)}</small>"

        if task.type == "system":
            lines.append(f'    {task.id}["{name}{actor}"]:::systemTask')
        else:
            lines.append(f'    {task.id}["{name}{actor}"]:::humanTask')

    # Decision nodes
    for decision in entities.decisions:
        question = _mermaid_escape(decision.question)
        lines.append(f'    {decision.id}{{"{question}"}}:::decision')

    # End node
    lines.append('    END(("✅ Fin")):::startEnd')
    lines.append("")

    # Connections
    # Start → first element
    if flow.start_event:
        lines.append(f"    START --> {flow.start_event}")

    # Flow connections
    for conn in flow.connections:
        if conn.condition:
            label = _mermaid_escape(conn.condition)
            lines.append(f'    {conn.from_id} -->|"{label}"| {conn.to_id}')
        else:
            lines.append(f"    {conn.from_id} --> {conn.to_id}")

    # End connections
    for end_id in flow.end_events:
        lines.append(f"    {end_id} --> END")

    return "\n".join(lines)


def _mermaid_escape(text: str) -> str:
    """Escape special characters for Mermaid diagram labels."""
    text = text.replace('"', "'")
    text = text.replace("#", "")
    text = text.replace("&", "et")
    text = text.replace("<", "‹")
    text = text.replace(">", "›")
    # Truncate long labels
    if len(text) > 50:
        text = text[:47] + "..."
    return text

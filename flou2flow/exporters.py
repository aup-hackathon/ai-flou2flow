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


    return workflow

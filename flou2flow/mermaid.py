"""Mermaid diagram generator for Flou2Flow pipeline results."""

from __future__ import annotations

from .models import ProcessEntities, ProcessFlow


def generate_mermaid_diagram(entities: ProcessEntities, flow: ProcessFlow) -> str:
    """
    Generate a Mermaid flowchart from extracted entities and flow.
    Returns a graph TD string compatible with Mermaid.js.
    """
    lines: list[str] = [
        "graph TD",
        "    classDef startEnd fill:#10b981,stroke:#059669,color:#fff,stroke-width:2px",
        "    classDef task fill:#6366f1,stroke:#4f46e5,color:#fff,stroke-width:2px",
        "    classDef decision fill:#f59e0b,stroke:#d97706,color:#fff,stroke-width:2px",
        "    classDef humanTask fill:#8b5cf6,stroke:#7c3aed,color:#fff,stroke-width:2px",
        "    classDef systemTask fill:#06b6d4,stroke:#0891b2,color:#fff,stroke-width:2px",
        "",
        "    START((\"🚀 Début\")):::startEnd",
    ]

    # Build actor lookup for task labels
    actor_map = {a.id: a.name for a in entities.actors}

    # Emit task nodes
    for task in entities.tasks:
        actor_label = actor_map.get(task.actor_id, "")
        actor_suffix = f"<br/><small>👤 {actor_label}</small>" if actor_label else ""
        node_class = "humanTask" if task.type == "human" else "systemTask"
        lines.append(
            f"    {task.id}[\"{task.name}{actor_suffix}\"]:::{node_class}"
        )

    # Emit decision nodes
    for decision in entities.decisions:
        lines.append(
            f"    {decision.id}{{\"  {decision.question}\"}}:::decision"
        )

    lines.append("    END((\"✅ Fin\")):::startEnd")
    lines.append("")

    # Start event → first node
    if flow.start_event:
        lines.append(f"    START --> {flow.start_event}")

    # Connections
    end_events_set = set(flow.end_events)
    for conn in flow.connections:
        from_id = conn.from_id
        to_id = conn.to_id

        # If target is a declared end event that has no node, route to END
        target = "END" if to_id in end_events_set and _is_unknown_node(to_id, entities) else to_id

        if conn.condition:
            lines.append(f"    {from_id} -->|\"{conn.condition}\"| {target}")
        else:
            lines.append(f"    {from_id} --> {target}")

    # End events that are real nodes → wire to END
    for ev in flow.end_events:
        if not _is_unknown_node(ev, entities):
            lines.append(f"    {ev} --> END")

    return "\n".join(lines)


def _is_unknown_node(node_id: str, entities: ProcessEntities) -> bool:
    """Return True if the node_id is not a known task or decision."""
    known = {t.id for t in entities.tasks} | {d.id for d in entities.decisions}
    return node_id not in known

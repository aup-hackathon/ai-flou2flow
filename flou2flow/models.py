"""Pydantic models for workflow data structures."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

# ── Step 1: Context Understanding ──────────────────────────────────────────

class ProcessContext(BaseModel):
    """Result of context understanding step."""
    summary: str = Field(description="Clear summary of the business process")
    domain: str = Field(description="Business domain (e.g., HR, Finance, Logistics)")
    objective: str = Field(description="Main objective of the process")
    stakeholders: list[str] = Field(default_factory=list, description="Key stakeholders")
    language: str = Field(default="fr", description="Detected language of input")


# ── Step 2: Entity Extraction ──────────────────────────────────────────────

class Actor(BaseModel):
    """A role or person involved in the process."""
    id: str
    name: str
    role: str = ""
    description: str = ""


class Task(BaseModel):
    """A task or activity in the process."""
    id: str
    hash: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Unique hashed identifier")
    node_type: str = Field(default="task", description="Type of the node for graph rendering")
    name: str
    description: str = ""
    actor_id: str = ""
    type: str = "human"  # human, system, manual


class Decision(BaseModel):
    """A decision point in the process."""
    id: str
    hash: str = Field(default_factory=lambda: uuid.uuid4().hex, description="Unique hashed identifier")
    node_type: str = Field(default="decision", description="Type of the node for graph rendering")
    question: str
    conditions: list[Condition] = Field(default_factory=list)


class Condition(BaseModel):
    """A condition branch from a decision."""
    label: str
    target_id: str


class DataObject(BaseModel):
    """A data object or document used in the process."""
    id: str
    name: str
    type: str = "document"  # document, form, email, data


class BusinessRule(BaseModel):
    """A business rule or constraint."""
    id: str
    description: str
    applies_to: str = ""


class ProcessEntities(BaseModel):
    """All extracted entities from the process description."""
    actors: list[Actor] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    data_objects: list[DataObject] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)


# ── Step 3: Flow Construction ──────────────────────────────────────────────

class FlowConnection(BaseModel):
    """A connection between two elements in the flow."""
    from_id: str
    to_id: str
    condition: str = ""  # Optional condition label


class ParallelBranch(BaseModel):
    """A parallel branch in the flow."""
    fork_after: str
    branches: list[list[str]] = Field(default_factory=list)
    join_before: str = ""


class ProcessFlow(BaseModel):
    """The structured process flow."""
    start_event: str = ""
    end_events: list[str] = Field(default_factory=list)
    connections: list[FlowConnection] = Field(default_factory=list)
    parallel_branches: list[ParallelBranch] = Field(default_factory=list)


# ── Full Pipeline Result ───────────────────────────────────────────────────

class PipelineResult(BaseModel):
    """Complete result of the Flou2Flow pipeline."""
    context: ProcessContext | None = None
    entities: ProcessEntities | None = None
    flow: ProcessFlow | None = None
    elsa_workflow: dict | None = None
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ── API Request/Response ───────────────────────────────────────────────────

class QueueRequest(BaseModel):
    """API request for task dispatch."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session UUID — propagated to NATS payloads")
    workflow: str = Field(description="One of: full, process, elsa")
    input_text: str = Field(description="Unstructured business process description")
    mode: str = Field(default="auto", description="Execution mode (auto, interactive)")
    model: str | None = Field(default=None, description="Optional model override (e.g., 'elsa', 'mistral')")
    image_data: str | None = Field(default=None, description="Base64 encoded image data for multimodal processing")


class AgentRequest(BaseModel):
    """API request for agentic system."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Session UUID — propagated to NATS payloads")
    task: str = Field(description="User task for the agentic system")
    mode: str = Field(default="auto", description="Execution mode (auto, interactive)")
    model: str | None = Field(default=None, description="Optional model override")
    image_data: str | None = Field(default=None, description="Base64 encoded image data for multimodal processing")


class AgentResponse(BaseModel):
    """Structured response from the agentic system."""
    result: str
    steps_taken: list[str] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)


class StepResult(BaseModel):
    """Result of a single pipeline step."""
    step_name: str
    step_number: int
    status: str  # "success", "error", "processing"
    data: dict = Field(default_factory=dict)
    error: str = ""


class QARequest(BaseModel):
    """API request for Q&A Agent."""
    input_text: str = Field(description="Unstructured business process description")
    context: dict | None = Field(default=None, description="Current process context if any")
    model: str | None = Field(default=None, description="Optional model override")
    image_data: str | None = Field(default=None, description="Base64 encoded image data for multimodal processing")


class QAResponse(BaseModel):
    """Structured response from the Q&A Agent."""
    questions: list[str] = Field(description="List of clarifying questions to fill gaps")
    gaps_identified: list[str] = Field(description="List of identified gaps or ambiguities")
    thought: str = Field(description="Agent's reasoning about the gaps")


# ── NATS Payload Schemas (for documentation / type hints) ─────────────────

class NatsTaskResult(BaseModel):
    """Exact schema published to ai.tasks.result (Backend_Issues.md BE-10)."""
    session_id: str
    workflow_json: dict          # Elsa-compatible workflow
    elements_json: dict          # Full pipeline structure (context, entities, flow)
    ai_summary: str              # Plain-language process summary
    confidence: float            # 0.0–1.0
    questions: list[str]         # Unanswered questions (Interactive mode)


class NatsTaskProgress(BaseModel):
    """Exact schema published to ai.tasks.progress (Backend_Issues.md BE-10/BE-16)."""
    session_id: str
    agent_name: str              # e.g. "pipeline", "qa_agent"
    status: str                  # "running" | "completed" | "failed"
    progress_pct: int            # 0–100
    message: str = ""

"""Pydantic models for workflow data structures."""

from __future__ import annotations

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
    name: str
    description: str = ""
    actor_id: str = ""
    type: str = "human"  # human, system, manual


class Decision(BaseModel):
    """A decision point in the process."""
    id: str
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

class ProcessRequest(BaseModel):
    """API request to process a business need."""
    input_text: str = Field(description="Unstructured business process description")
    language: str = Field(default="auto", description="Input language (auto, fr, en)")
    mode: str = Field(default="auto", description="Execution mode (auto, interactive)")
    image_data: str | None = Field(default=None, description="Base64 encoded image data for multimodal processing")


class QueueRequest(BaseModel):
    """API request for task dispatch."""
    workflow: str = Field(description="One of: full, process, elsa")
    input_text: str = Field(description="Unstructured business process description")
    mode: str = Field(default="auto", description="Execution mode (auto, interactive)")
    image_data: str | None = Field(default=None, description="Base64 encoded image data for multimodal processing")


class AgentRequest(BaseModel):
    """API request for agentic system."""
    task: str = Field(description="User task for the agentic system")
    mode: str = Field(default="auto", description="Execution mode (auto, interactive)")
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

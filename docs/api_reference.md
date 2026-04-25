# API Reference and Gateway

Flou2Flow provides a unified gateway for multimodal ingestion and structured workflow generation.

## The /api/input Gateway

The system provides a unified entry point for X to Text transformation via the /api/input endpoint.

1. Protocol: Accepts combinations of raw text and base64 encoded files (Audio, Image, PDF).
2. Processing: Executes file signature detection followed by raw semantic extraction.
3. Optimization: Applies High Density Context Optimization to the aggregated data.
4. Output: Returns a professional version of the business process optimized for downstream Large Language Models.

## Endpoint Documentation

### Input Preprocessing

**POST /api/input**

Transforms raw multimodal input into token optimized text.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| input_text | string | Optional raw text or notes |
| file_data | string | Base64 encoded content of the file |
| file_name | string | Name of the file including extension |

**Request Example**
```json
{
  "input_text": "Meeting notes about the new onboarding process.",
  "file_data": "base64...data",
  "file_name": "onboarding.mp3"
}
```

**Response Example**
```json
{
  "success": true,
  "type": "AUDIO",
  "result": "The onboarding process starts with a welcome email followed by a technical setup task.",
  "optimized_text": "The onboarding process starts with a welcome email followed by a technical setup task."
}
```

### Synchronous Workflow Generation

**POST /api/workflow/generate**

Executes the full pipeline and returns the structured result immediately.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| input_text | string | Unstructured process description |
| workflow | string | Type of output required (full, process, elsa) |
| mode | string | Execution mode (auto or interactive) |
| file_data | string | Optional base64 file data |
| file_name | string | Optional file name |

**Request Example**
```json
{
  "input_text": "When a user signs up, send a welcome email. Then, if they are premium, activate the dashboard.",
  "workflow": "elsa"
}
```

**Response Example (elsa mode)**
```json
{
  "id": "uuid",
  "name": "User Signup Process",
  "root": {
    "type": "Elsa.Flowchart",
    "activities": [...],
    "connections": [...]
  }
}
```

**Response Example (full mode)**
```json
{
  "success": true,
  "steps_completed": ["context_understanding", "entity_extraction", "flow_construction", "workflow_generation"],
  "context": {...},
  "entities": {...},
  "flow": {...},
  "elsa_workflow": {...},
  "bpmn_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "mermaid_diagram": "graph TD..."
}
```

### Asynchronous Workflow Dispatch

**POST /api/workflow/queue**

Adds a task to the background queue and returns a session identifier.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| session_id | string | Unique identifier for tracking progress |
| input_text | string | Unstructured process description |
| workflow | string | Type of output required |
| mode | string | Execution mode |

**Request Example**
```json
{
  "session_id": "session_123",
  "input_text": "Long process description...",
  "workflow": "full"
}
```

**Response Example**
```json
{
  "session_id": "session_123"
}
```

### Agentic Task Execution

**POST /api/agent**

Runs a multi agent system to handle complex reasoning tasks.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| task | string | The objective for the agentic system |
| mode | string | Execution mode (auto or interactive) |
| file_data | string | Optional base64 file data |
| file_name | string | Optional file name |

**Request Example**
```json
{
  "task": "Analyze the recruitment process and identify potential bottlenecks.",
  "mode": "auto"
}
```

**Response Example**
```json
{
  "result": "The bottleneck is located at the interview scheduling phase.",
  "steps_taken": ["Step 1: Context analysis", "Step 2: Bottleneck identification"],
  "tool_calls": []
}
```

### Gap Detection and Question Generation

**POST /api/qa/generate**

Analyzes the process for missing information and generates clarifying questions.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| input_text | string | Process description to analyze |
| context | object | Existing process context if available |

**Request Example**
```json
{
  "input_text": "The user submits a form. Then we process it."
}
```

**Response Example**
```json
{
  "questions": ["Who is responsible for processing the form?", "What happens if the form is invalid?"],
  "gaps_identified": ["Missing actor for processing step", "Missing error handling logic"],
  "thought": "The input is too vague about the processing stage."
}
```

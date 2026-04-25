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

### Asynchronous Workflow Dispatch

**POST /api/workflow/queue**

Adds a task to the background queue and returns a session identifier.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| session_id | string | Unique identifier for tracking progress |
| input_text | string | Unstructured process description |
| workflow | string | Type of output required |
| mode | string | Execution mode |

### Agentic Task Execution

**POST /api/agent**

Runs a multi agent system to handle complex reasoning tasks.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| task | string | The objective for the agentic system |
| mode | string | Execution mode (auto or interactive) |
| file_data | string | Optional base64 file data |
| file_name | string | Optional file name |

### Gap Detection and Question Generation

**POST /api/qa/generate**

Analyzes the process for missing information and generates clarifying questions.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| input_text | string | Process description to analyze |
| context | object | Existing process context if available |

# System Architecture and AI Design System

The Flou2Flow architecture is engineered for distributed AI reasoning across specialized, low parameter models.

## Multimodal Pipeline Architecture

The following diagram illustrates the information flow from raw multimodal ingestion to structured workflow generation.

```mermaid
graph TD
    subgraph "Input Layer (Multimodal)"
        Voice["Voice Data (.mp3, .wav)"] --> Whisper[Whisper Base]
        PDF["Document Extraction (.pdf)"] --> PyMuPDF[PyMuPDF Text Extraction]
        Image["Image Analysis (.png, .jpg)"] --> Vision[Vision LLM / OCR]
        RawText["Raw Text Input"] --> Pruning[Semantic Pruner]
    end

    subgraph "Pro Context Layer (/api/input)"
        Whisper --> Aggregator
        PyMuPDF --> Aggregator
        Vision --> Aggregator
        Pruning --> Aggregator
        Aggregator --> Optimizer["Context Optimizer (SmolLM)"]
    end

    subgraph "Reasoning Layer (Pipeline)"
        Optimizer --> Context["Context Understanding"]
        Context --> Entities["Entity Extraction"]
        Entities --> Flow["Flow Construction"]
    end

    subgraph "Output Layer"
        Flow --> Elsa["Elsa Workflow (JSON)"]
        Flow --> BPMN["BPMN 2.0 (XML)"]
        Flow --> Mermaid["Mermaid Diagram"]
    end
```

## AI Design System

The Flou2Flow AI Design System is built on the principle of heterogeneous model orchestration. Instead of a monolithic approach, we utilize a specialized matrix of lightweight models to achieve high performance on edge hardware.

### Model Matrix

| Engine | Core Model | Primary Responsibility | Optimization Strategy |
| :--- | :--- | :--- | :--- |
| Cleaning Engine | SmolLM 135M | Semantic noise removal and text distillation | Maximum token density |
| Analytical Engine | Qwen2 0.5B / 1.5B | Entity extraction and logical mapping | Grammar constrained JSON |
| Vision Engine | Llava / Moondream | Diagram analysis and OCR extraction | Spatial process reconstruction |
| Transcription Engine | Whisper Base | Audio to text conversion | Local CPU bound inference |

### Core Design Principles

1. Task Atomicity: Every AI task is broken down into its smallest logical component to allow for targeted model selection.
2. Contextual Isolation: Only the minimum required context is passed to the AI engines, managed via stable content hashing.
3. Structural Enforcement: We rely on mathematical grammar constraints rather than complex prompting to ensure data integrity.

## Messaging Infrastructure (NATS)

Flou2Flow utilizes **NATS** as its high-performance, asynchronous messaging backbone. This allows the system to handle long-running AI reasoning tasks without blocking the primary API gateway.

### Event-Driven Communication

The system communicates across specialized subjects to coordinate the multi-agent pipeline:

- `ai.tasks.new`: Subscribed to for incoming workflow generation requests containing raw context or document references.
- `ai.tasks.progress`: Published to by agents to provide real-time updates (0-100%) and status messages to the frontend.
- `ai.tasks.result`: Published to when the pipeline completes, delivering the final Elsa JSON, BPMN XML, and semantic summaries.

### Reliability and Persistence

Every message includes a mandatory `session_id` (UUID) to ensure end-to-end traceability. The use of NATS enables seamless scaling of "worker" nodes that can process complex reasoning tasks independently of the web server.

## Industry Standard Interoperability (BPMN 2.0)

While the primary output format is Elsa Workflows JSON, Flou2Flow ensures industry-wide compatibility through a native **BPMN 2.0** export engine.

### XML Generation Strategy

The system maps internal AI reasoning structures directly to the standard BPMN XML schema:

- **Process Flow**: Correctly handles start events, sequence flows, and end events.
- **Human Interaction**: Maps "human" tasks to `bpmn:userTask` elements.
- **Automation**: Maps "system" tasks to `bpmn:serviceTask` elements.
- **Logic**: Maps decision nodes to `bpmn:exclusiveGateway` for branching logic.

This allows generated workflows to be imported into professional Business Process Management (BPM) suites such as Camunda, Signavio, or Bizagi for formal validation and execution.

### System Workflow Lifecycle

The coordination between these engines follows a linear optimization path:

1. Ingestion: Raw data is captured and routed to the appropriate specialized extraction engine based on file type.
2. Distillation: The Cleaning Engine removes noise and produces a high density semantic summary.
3. Decomposition: The Analytical Engine breaks the summary into discrete entities such as Actors and Tasks.
4. Structuring: The system converts the entities into TOON format to minimize token load during the final logic phase.
5. Synthesis: The Final Pipeline constructs the logical connections and exports the result as an Elsa compatible workflow.

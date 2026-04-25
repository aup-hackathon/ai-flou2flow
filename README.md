# Flou2Flow: AI Design System and Architecture

**Transforming Unstructured Business Requirements into Executable High Density Workflows.**

Flou2Flow is a high performance AI orchestration system designed to convert multimodal business inputs (Voice, PDF, Images, Text) into structured Elsa Workflows. Engineered for edge computing, it utilizes a heterogeneous matrix of lightweight models optimized for maximum token efficiency.

## Core Documentation

Explore the detailed architecture and optimization methodologies of the Flou2Flow system:

1. [Architecture and Design System](docs/architecture.md): Overview of the multimodal pipeline, model matrix, and core design principles.
2. [Token Optimization and Semantic Engineering](docs/optimization.md): Detailed explanation of TOON, semantic pruning, stable hashing, and benchmarking.
3. [API Reference and Gateway](docs/api_reference.md): Full documentation of all endpoints, parameters, and the multimodal input gateway.

## Models Used

Current default models in use now:

| Engine | Env Variable | Model |
| :--- | :--- | :--- |
| Primary reasoning | `LLM_MODEL` | `qwen2:0.5b` |
| Cleaning / aggregation | `CLEANING_MODEL` | `smollm:135m` |
| Vision / OCR | `VISION_MODEL` | `llava:7b` |
| Voice transcription | `WHISPER_MODEL` | `base` (OpenAI Whisper) |

### Post-Competition Roadmap: Vision Model Upgrade

> [!NOTE]
> **Planned Switch to Flamingo (or equivalent ultra-light model)**: After the hackathon competition, we will replace `llava:7b` with a **Flamingo-based** or similar ultra-lightweight computer vision model.
>
> **Why?** Flamingo and ultra-lightweight vision models offer superior token optimization and efficiency for multimodal tasks. This transition is essential for better model management and reducing our token budget during image processing, perfectly aligning with our Zero Waste token philosophy.


## Project Vision

The mission of Flou2Flow is to eliminate the requirement for massive reasoning models in structural business tasks. By implementing a Zero Waste token philosophy and specialized model routing, we deliver professional grade workflow extraction on resource constrained hardware.

1. High Density Context: Reducing structural noise to ensure maximum information flow.
2. Heterogeneous Orchestration: Using the right model for the right task at the right time.
3. Deterministic Integrity: Ensuring structural consistency through mathematical grammar constraints and stable hashing.

---

**Keywords:** `AI Orchestration` • `Multi-agent Systems` • `Workflow Automation` • `BPMN 2.0` • `NATS Messaging` • `Elsa Workflows` • `Multimodal AI` • `Edge Computing` • `Token Optimization` • `Heterogeneous Models`

*Architecture documentation for Flou2Flow Core System.*

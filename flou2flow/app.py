"""FastAPI application for Flou2Flow — API only."""

from __future__ import annotations

import logging
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .agent import FlouAgent
from .config import settings
from .llm import llm_client
from .mermaid import generate_mermaid_diagram
from .models import AgentRequest, AgentStep, InputRequest, InputResponse, MultimodalResult, PipelineResult, ProcessContext, QARequest, QueueRequest
from .multimodal import processor
from .nats_handler import nats_handler
from .pipeline import run_pipeline
from .prompts import MULTIMODAL_SYSTEM_PROMPT, MULTIMODAL_USER_PROMPT
from .utils import semantic_prune

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_confidence(result: PipelineResult) -> float:
    """
    Derive a confidence score (0.0–1.0) from the pipeline result.
    - 4 possible steps → each adds 0.25
    - Subtract 0.1 per error, floored at 0.0
    """
    steps_score = len(result.steps_completed) / 4.0
    error_penalty = len(result.errors) * 0.1
    return max(0.0, min(1.0, steps_score - error_penalty))


def _build_elements_json(result: PipelineResult) -> dict:
    """Build the full elements_json structure the backend expects."""
    return {
        "context": result.context.model_dump() if result.context else None,
        "entities": result.entities.model_dump() if result.entities else None,
        "flow": result.flow.model_dump() if result.flow else None,
        "steps_completed": result.steps_completed,
        "errors": result.errors,
    }


# ─── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to NATS and start subscribers on startup."""
    try:
        await nats_handler.connect()

        # Callback to handle tasks from NATS (ai.tasks.new)
        async def nats_task_callback(session_id: str, data: dict):
            workflow = data.get("workflow", "full")
            input_text = data.get("input_text", "")
            mode = data.get("mode", "auto")
            image_data = data.get("image_data")
            model = data.get("model")
            await run_workflow_task(session_id, workflow, input_text, mode, image_data, model)

        await nats_handler.subscribe_tasks(nats_task_callback)
        await nats_handler.subscribe_preprocess()
        logger.info("NATS connected and subscribers started.")
    except Exception as e:
        logger.warning(f"Failed to connect to NATS: {e}. Continuing without NATS.")

    yield

    await nats_handler.disconnect()
    await llm_client.close()


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Flou2Flow",
    description="Transform fuzzy business needs into executable workflows using Mistral 7B",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "nats_connected": nats_handler.is_connected,
    }


async def process_multimodal_input(
    input_text: str,
    file_data: str | None = None,
    file_name: str | None = None
) -> dict:
    """Auto-detects file type from extension and routes to appropriate local processor."""
    # Pro Method: Semantic Pruning
    input_text = semantic_prune(input_text)
    
    extra_context = []
    
    if file_data and file_name:
        ext = file_name.lower().split(".")[-1]

        # 1. Route to Voice (Audio extensions)
        if ext in ["mp3", "wav", "m4a", "ogg", "flac"]:
            logger.info(f"Auto-routed {file_name} to Whisper...")
            transcript = await processor.process_voice(file_data)
            extra_context.append(f"[Voice Transcript]: {transcript}")

        # 2. Route to PDF
        elif ext == "pdf":
            logger.info(f"Auto-routed {file_name} to PDF Engine...")
            pdf_content = await processor.process_pdf(file_data)
            extra_context.append(f"[PDF Content]:\n{pdf_content}")

        # 3. Route to Image (Vision extensions)
        elif ext in ["png", "jpg", "jpeg", "webp", "bmp"]:
            logger.info(f"Auto-routed {file_name} to Moondream Vision...")
            image_desc = await processor.process_image(file_data)
            extra_context.append(f"[Image Analysis]: {image_desc}")

    # Combine all into a single context for the cleaning agent
    combined_input = f"{input_text}\n\n" + "\n\n".join(extra_context)
    user_prompt = MULTIMODAL_USER_PROMPT.format(input_text=combined_input)
    
    try:
        logger.info("Structuring aggregated multimodal context...")
        response = await llm_client.chat(
            system_prompt=MULTIMODAL_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model=settings.CLEANING_MODEL,
            json_mode=True,
            response_schema=MultimodalResult,
        )
        data = llm_client.parse_json_response(response)
        logger.info(f"Multimodal cleaning model output: {json.dumps(data, indent=2)}")
        if "result" not in data:
            data["result"] = combined_input
        if "type" not in data:
            data["type"] = "UNKNOWN"
        return data
    except Exception as e:
        logger.error(f"Multimodal structuring failed: {e}")
        return {"result": combined_input, "type": "UNKNOWN"}



async def run_workflow_task(
    session_id: str,
    workflow: str,
    input_text: str,
    mode: str,
    file_data: str | None = None,
    file_name: str | None = None
):
    """
    Background task: run the pipeline and publish progress + result to NATS
    using the schema required by the backend (BE-10 / §4.3).
    """
    try:
        # ── Step 0: Multimodal ─────────────────────────────────
        await nats_handler.publish_progress(
            session_id=session_id,
            agent_name="pipeline",
            status="running",
            progress_pct=10,
            message="Processing input (multimodal check)",
        )
        multimodal_data = await process_multimodal_input(
            input_text, 
            file_data=file_data, 
            file_name=file_name
        )
        processed_text = multimodal_data["result"]

        # ── Step 1–4: Pipeline ─────────────────────────────────
        await nats_handler.publish_progress(
            session_id=session_id,
            agent_name="pipeline",
            status="running",
            progress_pct=30,
            message="Running context understanding",
        )
        result = await run_pipeline(processed_text)

        await nats_handler.publish_progress(
            session_id=session_id,
            agent_name="pipeline",
            status="running",
            progress_pct=85,
            message=f"Pipeline done — {len(result.steps_completed)} steps completed",
        )

        # ── Interactive mode: generate questions ───────────────
        questions: list[str] = []
        if mode == "interactive" and result.context:
            try:
                agent = FlouAgent()
                qa = await agent.generate_questions(processed_text)
                questions = qa.questions
            except Exception as qa_err:
                logger.warning(f"QA agent failed: {qa_err}")

        # ── Build result payload ───────────────────────────────
        confidence = _compute_confidence(result)
        elements_json = _build_elements_json(result)
        ai_summary = result.context.summary if result.context else ""
        workflow_json = result.elsa_workflow or {}

        await nats_handler.publish_result(
            session_id=session_id,
            workflow_json=workflow_json,
            elements_json=elements_json,
            ai_summary=ai_summary,
            confidence=confidence,
            questions=questions,
        )

        await nats_handler.publish_progress(
            session_id=session_id,
            agent_name="pipeline",
            status="completed",
            progress_pct=100,
            message="Workflow generation complete",
        )

    except Exception as e:
        logger.error(f"Task error (session {session_id}): {e}", exc_info=True)
        await nats_handler.publish_progress(
            session_id=session_id,
            agent_name="pipeline",
            status="failed",
            progress_pct=100,
            message=str(e),
        )


@app.post("/api/workflow/queue")
async def generate_workflow_async(req: QueueRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous endpoint: add task to background and return session_id.
    """
    logger.info(f"Queue workflow [{req.workflow}] session={req.session_id}")

    background_tasks.add_task(
        run_workflow_task,
        req.session_id,
        req.workflow,
        req.input_text,
        req.mode,
        file_data=req.file_data,
        file_name=req.file_name
    )
    return {"session_id": req.session_id}


@app.post("/api/workflow/generate")
async def generate_workflow_sync(req: QueueRequest):
    """
    Synchronous endpoint: run pipeline and return result directly.
    Also publishes to NATS with the correct backend schema.
    """
    logger.info(f"Sync workflow [{req.workflow}] session={req.session_id}")

    try:
        multimodal_data = await process_multimodal_input(
            req.input_text, 
            req.file_data, 
            req.file_name
        )
        processed_text = multimodal_data["result"]
        result = await run_pipeline(processed_text)

        confidence = _compute_confidence(result)
        elements_json = _build_elements_json(result)
        ai_summary = result.context.summary if result.context else ""
        workflow_json = result.elsa_workflow or {}

        # Publish to NATS so the backend receives it even on HTTP calls
        questions: list[str] = []
        if req.mode == "interactive" and result.context:
            try:
                agent = FlouAgent()
                qa = await agent.generate_questions(processed_text)
                questions = qa.questions
            except Exception as qa_err:
                logger.warning(f"QA agent failed: {qa_err}")

        await nats_handler.publish_result(
            session_id=req.session_id,
            workflow_json=workflow_json,
            elements_json=elements_json,
            ai_summary=ai_summary,
            confidence=confidence,
            questions=questions,
        )

        # HTTP response — return the shape the user requested
        if req.workflow == "elsa":
            return workflow_json

        elif req.workflow == "process":
            mermaid_diagram = ""
            if result.entities and result.flow:
                try:
                    mermaid_diagram = generate_mermaid_diagram(result.entities, result.flow)
                except Exception as md_err:
                    logger.warning(f"Mermaid generation failed: {md_err}")

            return {
                "success": len(result.errors) == 0,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
                "context": result.context.model_dump() if result.context else None,
                "entities": result.entities.model_dump() if result.entities else None,
                "flow": result.flow.model_dump() if result.flow else None,
                "elsa_workflow": workflow_json,
                "mermaid_diagram": mermaid_diagram,
            }

        else:  # full — matches the confirmed schema
            mermaid_diagram = ""
            if result.entities and result.flow:
                try:
                    mermaid_diagram = generate_mermaid_diagram(result.entities, result.flow)
                except Exception as md_err:
                    logger.warning(f"Mermaid generation failed: {md_err}")

            return {
                "success": len(result.errors) == 0,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
                "context": result.context.model_dump() if result.context else None,
                "entities": result.entities.model_dump() if result.entities else None,
                "flow": result.flow.model_dump() if result.flow else None,
                "elsa_workflow": workflow_json,
                "mermaid_diagram": mermaid_diagram,
            }

    except Exception as e:
        logger.error(f"Sync workflow generation failed: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    """Run an agentic system to handle a task."""
    logger.info(f"Agent request: {req.task} (mode: {req.mode}, session={req.session_id})")

    multimodal_data = await process_multimodal_input(
        req.task, 
        req.file_data, 
        req.file_name
    )
    processed_task = multimodal_data["result"]
    agent = FlouAgent()

    try:
        await nats_handler.publish_progress(
            session_id=req.session_id,
            agent_name="flou_agent",
            status="running",
            progress_pct=10,
            message="Agent started",
        )
        response = await agent.run(processed_task, session_id=req.session_id)

        await nats_handler.publish_progress(
            session_id=req.session_id,
            agent_name="flou_agent",
            status="completed",
            progress_pct=100,
            message="Agent completed",
        )
        return response
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        await nats_handler.publish_progress(
            session_id=req.session_id,
            agent_name="flou_agent",
            status="failed",
            progress_pct=100,
            message=str(e),
        )
        return JSONResponse(status_code=500, content={"error": f"Agent error: {str(e)}"})


@app.post("/api/qa/generate")
async def generate_qa_questions(req: QARequest):
    """Generate clarifying questions from process gaps."""
    logger.info(f"QA request: {len(req.input_text)} chars (multimodal: {req.image_data is not None})")

    multimodal_data = await process_multimodal_input(
        req.input_text, 
        req.file_data, 
        req.file_name
    )
    processed_text = multimodal_data["result"]
    agent = FlouAgent()

    try:
        response = await agent.generate_questions(processed_text, context=req.context)
        return response
    except Exception as e:
        logger.error(f"QA Agent failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/input", response_model=InputResponse)
async def preprocess_input(req: InputRequest):
    """
    Pro-Context Endpoint: Transforms raw multimodal input into 
    token-optimized, semantically dense text.
    """
    logger.info(f"Pre-processing input: {req.file_name or 'Text'}")
    try:
        data = await process_multimodal_input(
            req.input_text,
            req.file_data,
            req.file_name
        )
        return InputResponse(
            success=True,
            type=data.get("type", "UNKNOWN"),
            result=data.get("result", ""),
            optimized_text=data.get("result", "")
        )
    except Exception as e:
        logger.error(f"Input preprocessing failed: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting Flou2Flow on {settings.HOST}:{settings.PORT} (Models: {settings.LLM_MODEL}, {settings.VISION_MODEL})")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)

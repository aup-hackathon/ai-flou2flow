"""FastAPI application for Flou2Flow — API only."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid

from .config import settings
from .models import QueueRequest, AgentRequest, AgentResponse, QARequest
from .pipeline import run_pipeline
from .llm import llm_client
from .agent import FlouAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Job storage (in-memory for demo)
JOBS = {}

# Create FastAPI app
app = FastAPI(
    title="Flou2Flow",
    description="Transform fuzzy business needs into executable workflows using Mistral 7B",
    version="0.1.0",
    docs_url="/docs",
)


@app.on_event("shutdown")
async def shutdown():
    await llm_client.close()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
    }


async def process_multimodal_input(input_text: str, image_data: str | None) -> str:
    """If image data is provided, analyze it and enrich the input text."""
    if not image_data:
        return input_text
    
    try:
        logger.info("Analyzing multimodal input (image)...")
        description = await llm_client.vision_chat(
            prompt="Analyze this process diagram or whiteboard drawing. Describe the actors, tasks, and flow in detail so it can be transformed into a structured workflow.",
            image_data=image_data
        )
        enriched_text = f"{input_text}\n\n[Diagram Description]:\n{description}"
        return enriched_text
    except Exception as e:
        logger.error(f"Multimodal analysis failed: {e}")
        return f"{input_text}\n\n(Note: Image analysis failed: {str(e)})"


async def run_workflow_task(job_id: str, workflow: str, input_text: str, mode: str, image_data: str | None = None, model: str | None = None):
    """Background task to run the workflow."""
    JOBS[job_id] = {"status": "processing", "workflow": workflow, "mode": mode}
    try:
        # Step 0: Multimodal processing
        processed_text = await process_multimodal_input(input_text, image_data)
        
        result = await run_pipeline(processed_text, model=model)
        
        if workflow == "full":
            data = {
                "success": len(result.errors) == 0,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
                "context": result.context.model_dump() if result.context else None,
                "entities": result.entities.model_dump() if result.entities else None,
                "flow": result.flow.model_dump() if result.flow else None,
                "elsa_workflow": result.elsa_workflow,
            }
        elif workflow == "process":
            data = {
                "success": len(result.errors) == 0,
                "steps_completed": [s for s in result.steps_completed if s != "workflow_generation"],
                "context": result.context.model_dump() if result.context else None,
                "entities": result.entities.model_dump() if result.entities else None,
                "flow": result.flow.model_dump() if result.flow else None,
            }
        elif workflow == "elsa":
            data = result.elsa_workflow
        else:
            data = {"error": f"Unknown workflow: {workflow}"}
            
        JOBS[job_id] = {"status": "completed", "result": data}
    except Exception as e:
        logger.error(f"Background task error: {e}", exc_info=True)
        JOBS[job_id] = {"status": "failed", "error": str(e)}


@app.post("/api/queue")
async def queue_task(req: QueueRequest, background_tasks: BackgroundTasks):
    """Enqueue a workflow task and return a job ID immediately."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "queued", "mode": req.mode}
    
    background_tasks.add_task(run_workflow_task, job_id, req.workflow, req.input_text, req.mode, req.image_data, req.model)
    
    return {"job_id": job_id, "status": "queued", "mode": req.mode}


@app.get("/api/queue/{job_id}")
async def get_job_status(job_id: str):
    """Get the status and result of a queued job."""
    job = JOBS.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return job


@app.post("/api/agent")
async def run_agent(req: AgentRequest):
    """Run an agentic system to handle a task."""
    logger.info(f"Agent request: {req.task} (mode: {req.mode}, multimodal: {req.image_data is not None})")
    
    # Process multimodal input for the agent as well
    processed_task = await process_multimodal_input(req.task, req.image_data)
    
    agent = FlouAgent()
    try:
        response = await agent.run(processed_task, mode=req.mode, model=req.model)
        return response
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Agent error: {str(e)}"})


@app.post("/api/qa/generate")
async def generate_qa_questions(req: QARequest):
    """Generate clarifying questions from process gaps."""
    logger.info(f"QA request: {len(req.input_text)} chars (multimodal: {req.image_data is not None})")
    
    # Process multimodal input if provided
    processed_text = await process_multimodal_input(req.input_text, req.image_data)
    
    agent = FlouAgent()
    try:
        response = await agent.generate_questions(processed_text, context=req.context, model=req.model)
        return response
    except Exception as e:
        logger.error(f"QA Agent error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"QA Agent error: {str(e)}"})

"""FastAPI application for Flou2Flow — API only."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid
import asyncio

from .config import settings
from .models import QueueRequest, AgentRequest, AgentResponse, QARequest
from .pipeline import run_pipeline
from .llm import llm_client
from .agent import FlouAgent
from .nats_handler import nats_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Flou2Flow",
    description="Transform fuzzy business needs into executable workflows using Mistral 7B",
    version="0.1.0",
    docs_url="/docs",
)


@app.on_event("startup")
async def startup():
    """Connect to NATS and start subscribers on startup."""
    await nats_handler.connect()
    
    # Callback to handle tasks from NATS
    async def nats_task_callback(job_id, data):
        workflow = data.get("workflow", "full")
        input_text = data.get("input_text", "")
        mode = data.get("mode", "auto")
        image_data = data.get("image_data")
        model = data.get("model")
        await run_workflow_task(job_id, workflow, input_text, mode, image_data, model)

    # Start subscriptions
    await nats_handler.subscribe_tasks(nats_task_callback)
    await nats_handler.subscribe_preprocess()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    await nats_handler.disconnect()
    await llm_client.close()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "nats_connected": nats_handler.is_connected,
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
    """Background task to run the workflow and report progress via NATS."""
    try:
        # Step 0: Multimodal processing
        await nats_handler.publish_progress(job_id, "multimodal_processing")
        processed_text = await process_multimodal_input(input_text, image_data)
        
        # Step 1: Run full pipeline
        await nats_handler.publish_progress(job_id, "pipeline_execution")
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
            
        # Step 2: Publish result
        await nats_handler.publish_result(job_id, data)
        
    except Exception as e:
        logger.error(f"Task error (job {job_id}): {e}", exc_info=True)
        await nats_handler.publish_result(job_id, {"error": str(e)})


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

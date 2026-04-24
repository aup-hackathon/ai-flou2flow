"""FastAPI application for Flou2Flow — API only."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .config import settings
from .models import ProcessRequest
from .pipeline import run_pipeline
from .llm import llm_client

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


@app.post("/api/process")
async def process_workflow(req: ProcessRequest):
    """Process unstructured text and generate a workflow.

    Runs the full 4-step pipeline:
    1. Context Understanding
    2. Entity Extraction
    3. Flow Construction
    4. Workflow Generation (Elsa JSON + Mermaid diagram)
    """
    logger.info(f"Processing request: {len(req.input_text)} chars")

    if not req.input_text.strip():
        return JSONResponse(status_code=400, content={"error": "Input text is required"})

    try:
        result = await run_pipeline(req.input_text)
        return {
            "success": len(result.errors) == 0,
            "elsa_workflow": result.elsa_workflow,
            "rest": {
                "context": result.context.model_dump() if result.context else None,
                "entities": result.entities.model_dump() if result.entities else None,
                "flow": result.flow.model_dump() if result.flow else None,
                "steps_completed": result.steps_completed,
                "errors": result.errors,
            }
        }
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": f"Pipeline error: {str(e)}"})


@app.get("/api/examples")
async def get_examples():
    """Get sample process descriptions for demo."""
    examples = [
        {
            "title": "Demande de congé",
            "text": (
                "Quand un employé veut prendre des congés, il doit d'abord vérifier son solde de congés "
                "dans le système RH. Ensuite, il remplit une demande de congé en précisant les dates "
                "souhaitées et le type de congé. La demande est envoyée à son manager direct qui peut "
                "l'approuver ou la refuser. Si le manager refuse, l'employé peut modifier sa demande. "
                "Si le manager approuve, la demande est transmise au service RH pour validation finale. "
                "Le RH vérifie la conformité et le solde disponible. Si tout est conforme, le congé est "
                "validé, le solde est mis à jour et l'employé reçoit une confirmation par email."
            ),
        },
        {
            "title": "Traitement réclamation client",
            "text": (
                "Un client contacte le service client pour signaler un problème. L'agent enregistre la "
                "réclamation dans le CRM. Si c'est un problème technique, elle va à l'équipe technique. "
                "Si c'est la facturation, elle va au service comptabilité. Pour les cas urgents, escalade "
                "au responsable. L'équipe analyse le problème, propose une solution et contacte le client. "
                "Si le client accepte, la réclamation est clôturée. Sinon, elle remonte au niveau supérieur."
            ),
        },
    ]
    return {"examples": examples}


def main():
    """Run the application with Uvicorn."""
    import uvicorn
    uvicorn.run("flou2flow.app:app", host=settings.HOST, port=settings.PORT, reload=True)

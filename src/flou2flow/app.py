"""FastAPI application for Flou2Flow."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings, TEMPLATES_DIR, STATIC_DIR
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
    description="Transform fuzzy business needs into executable workflows",
    version="0.1.0",
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    await llm_client.close()


# ═══════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Flou2Flow — Du flou au flow",
    })


@app.post("/api/process")
async def process_workflow(req: ProcessRequest):
    """Process unstructured text and generate a workflow.

    This is the main API endpoint that runs the full 4-step pipeline:
    1. Context Understanding
    2. Entity Extraction
    3. Flow Construction
    4. Workflow Generation
    """
    logger.info(f"Processing request: {len(req.input_text)} chars")

    if not req.input_text.strip():
        return JSONResponse(
            status_code=400,
            content={"error": "Input text is required"},
        )

    try:
        result = await run_pipeline(req.input_text)

        return {
            "success": len(result.errors) == 0,
            "steps_completed": result.steps_completed,
            "errors": result.errors,
            "context": result.context.model_dump() if result.context else None,
            "entities": result.entities.model_dump() if result.entities else None,
            "flow": result.flow.model_dump() if result.flow else None,
            "elsa_workflow": result.elsa_workflow,
            "mermaid_diagram": result.mermaid_diagram,
        }

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Pipeline error: {str(e)}"},
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
    }


@app.get("/api/examples")
async def get_examples():
    """Get sample process descriptions for demo purposes."""
    examples = [
        {
            "title": "Demande de congé",
            "description": "Processus de gestion des demandes de congé",
            "text": (
                "Quand un employé veut prendre des congés, il doit d'abord vérifier son solde de congés "
                "dans le système RH. Ensuite, il remplit une demande de congé en précisant les dates "
                "souhaitées et le type de congé (annuel, maladie, sans solde). La demande est envoyée "
                "à son manager direct qui peut l'approuver ou la refuser. Si le manager refuse, il doit "
                "indiquer le motif et l'employé peut modifier sa demande et la resoumettre. Si le manager "
                "approuve, la demande est transmise au service RH pour validation finale. Le RH vérifie "
                "la conformité avec la politique de l'entreprise et le solde disponible. Si tout est "
                "conforme, le congé est validé, le solde est mis à jour et l'employé reçoit une "
                "confirmation par email. En cas de problème, le RH contacte le manager pour discussion."
            ),
        },
        {
            "title": "Onboarding nouvel employé",
            "description": "Processus d'intégration d'un nouveau collaborateur",
            "text": (
                "L'intégration d'un nouveau collaborateur commence quand le RH reçoit la confirmation "
                "d'embauche. Le RH prépare le dossier administratif : contrat de travail, documents "
                "d'identité, RIB, mutuelle. En parallèle, le service IT prépare le poste de travail : "
                "ordinateur, comptes email, accès aux applications, badge d'accès. Le manager du nouveau "
                "collaborateur prépare le plan d'intégration avec les formations prévues et les objectifs "
                "de la période d'essai. Le jour J, le RH accueille le nouveau collaborateur, lui fait "
                "signer les documents, lui présente l'entreprise. Le IT lui remet son matériel et "
                "configure ses accès. Le manager lui présente l'équipe et lance le parcours d'intégration. "
                "Un point est fait à 1 mois, 3 mois et en fin de période d'essai pour valider l'intégration."
            ),
        },
        {
            "title": "Traitement d'une réclamation client",
            "description": "Processus de gestion des réclamations",
            "text": (
                "Un client contacte le service client par téléphone, email ou formulaire web pour "
                "signaler un problème. L'agent du service client enregistre la réclamation dans le "
                "système CRM avec les détails du problème, les coordonnées du client et la priorité "
                "estimée. Si la réclamation concerne un problème technique, elle est transmise à l'équipe "
                "technique. Si elle concerne la facturation, elle va au service comptabilité. Pour les "
                "cas urgents (client VIP ou problème bloquant), un escalade immédiate est faite au "
                "responsable du service concerné. L'équipe en charge analyse le problème, propose une "
                "solution et contacte le client. Si le client accepte la solution, la réclamation est "
                "clôturée et une enquête de satisfaction est envoyée. Si le client n'est pas satisfait, "
                "la réclamation remonte au niveau supérieur pour traitement spécial."
            ),
        },
    ]

    return {"examples": examples}


def main():
    """Run the application with Uvicorn."""
    import uvicorn
    uvicorn.run(
        "flou2flow.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )

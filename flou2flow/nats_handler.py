"""NATS messaging handler for Flou2Flow."""

import asyncio
import json
import logging
import uuid

from nats.aio.client import Client as NatsClient

from .config import settings

logger = logging.getLogger(__name__)

class NatsHandler:
    def __init__(self):
        self.nc = NatsClient()
        self.is_connected = False

    async def connect(self):
        """Connect to NATS server with a hard 3-second timeout."""
        try:
            await asyncio.wait_for(
                self.nc.connect(settings.NATS_URL),
                timeout=3.0
            )
            self.is_connected = True
            logger.info(f"Connected to NATS at {settings.NATS_URL}")
        except (TimeoutError, Exception) as e:
            logger.warning(f"NATS unavailable ({e}). Continuing without NATS.")
            self.is_connected = False

    async def disconnect(self):
        """Disconnect from NATS server."""
        if self.is_connected:
            await self.nc.close()
            self.is_connected = False
            logger.info("Disconnected from NATS")

    async def publish_result(
        self,
        session_id: str,
        workflow_json: dict,
        bpmn_xml: str | None,
        elements_json: dict,
        ai_summary: str,
        confidence: float,
        questions: list[str] | None = None,
    ):
        """
        Publish task result to ai.tasks.result.

        Payload schema (as per Backend_Issues.md BE-10 / Project-Plan §4.3):
            session_id     — UUID of the originating session
            workflow_json  — Generated Elsa workflow elements
            elements_json  — Full pipeline structure (context, entities, flow)
            ai_summary     — Plain-language process summary
            confidence     — Overall pipeline confidence score (0.0–1.0)
            questions[]    — Unanswered questions (Interactive mode only)
        """
        if not self.is_connected:
            logger.debug(f"NATS not connected — skipping publish_result for session {session_id}")
            return

        payload = {
            "session_id": session_id,
            "workflow_json": workflow_json,
            "bpmn_xml": bpmn_xml,
            "elements_json": elements_json,
            "ai_summary": ai_summary,
            "confidence": round(confidence, 4),
            "questions": questions or [],
        }
        await self.nc.publish("ai.tasks.result", json.dumps(payload).encode())
        logger.info(f"Published result for session {session_id} to ai.tasks.result")

    async def publish_progress(
        self,
        session_id: str,
        agent_name: str,
        status: str,          # "running" | "completed" | "failed"
        progress_pct: int,    # 0–100
        message: str = "",
    ):
        """
        Publish task progress to ai.tasks.progress.

        Payload schema (as per Backend_Issues.md BE-10/BE-16 / Project-Plan §4.3):
            session_id   — UUID of the originating session
            agent_name   — Which agent is running (e.g. "pipeline", "qa_agent")
            status       — "running" | "completed" | "failed"
            progress_pct — Completion percentage (0–100)
            message      — Optional human-readable status message
        """
        if not self.is_connected:
            return

        payload = {
            "session_id": session_id,
            "agent_name": agent_name,
            "status": status,
            "progress_pct": max(0, min(100, progress_pct)),
            "message": message,
        }
        await self.nc.publish("ai.tasks.progress", json.dumps(payload).encode())
        logger.debug(f"Progress [{agent_name}] {progress_pct}% — {message} (session {session_id})")

    async def subscribe_tasks(self, callback):
        """Subscribe to ai.tasks.new."""
        if not self.is_connected:
            return

        async def message_handler(msg):
            subject = msg.subject
            data = json.loads(msg.data.decode())
            logger.info(f"Received message on {subject}")

            # Use session_id as the primary identifier (fall back to new UUID)
            session_id = data.get("session_id", str(uuid.uuid4()))

            # Start background task via callback
            asyncio.create_task(callback(session_id, data))

        await self.nc.subscribe("ai.tasks.new", cb=message_handler)
        logger.info("Subscribed to ai.tasks.new")

    async def subscribe_preprocess(self):
        """Subscribe to document.preprocess."""
        if not self.is_connected:
            return

        async def preprocess_handler(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"Received preprocess request for document: {data.get('document_id')}")
            await self.nc.publish(
                "document.preprocessed",
                json.dumps({"status": "ok", "document_id": data.get("document_id")}).encode()
            )

        await self.nc.subscribe("document.preprocess", cb=preprocess_handler)
        logger.info("Subscribed to document.preprocess")


# Global NATS handler instance
nats_handler = NatsHandler()

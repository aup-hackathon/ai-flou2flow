"""NATS messaging handler for Flou2Flow."""

import json
import logging
import asyncio
from nats.aio.client import Client as NATS
from .config import settings
from .models import QueueRequest
import uuid

logger = logging.getLogger(__name__)

class NatsHandler:
    def __init__(self):
        self.nc = NATS()
        self.is_connected = False

    async def connect(self):
        """Connect to NATS server."""
        try:
            await self.nc.connect(settings.NATS_URL)
            self.is_connected = True
            logger.info(f"Connected to NATS at {settings.NATS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.is_connected = False

    async def disconnect(self):
        """Disconnect from NATS server."""
        if self.is_connected:
            await self.nc.close()
            self.is_connected = False
            logger.info("Disconnected from NATS")

    async def publish_result(self, job_id: str, result: dict):
        """Publish task result to NATS."""
        if not self.is_connected:
            return
        
        payload = {
            "job_id": job_id,
            "status": "completed",
            "result": result
        }
        await self.nc.publish("ai.tasks.result", json.dumps(payload).encode())
        logger.info(f"Published result for job {job_id} to ai.tasks.result")

    async def publish_progress(self, job_id: str, step: str, data: dict = None):
        """Publish task progress to NATS."""
        if not self.is_connected:
            return
        
        payload = {
            "job_id": job_id,
            "status": "processing",
            "step": step,
            "data": data
        }
        await self.nc.publish("ai.tasks.progress", json.dumps(payload).encode())
        logger.debug(f"Published progress for job {job_id} (step: {step})")

    async def subscribe_tasks(self, callback):
        """Subscribe to ai.tasks.new."""
        if not self.is_connected:
            await self.connect()

        async def message_handler(msg):
            subject = msg.subject
            reply = msg.reply
            data = json.loads(msg.data.decode())
            logger.info(f"Received message on {subject}")
            
            # Generate a job_id if not provided
            job_id = data.get("job_id", str(uuid.uuid4()))
            
            # Start background task via callback
            asyncio.create_task(callback(job_id, data))

        await self.nc.subscribe("ai.tasks.new", cb=message_handler)
        logger.info("Subscribed to ai.tasks.new")

    async def subscribe_preprocess(self):
        """Subscribe to document.preprocess."""
        if not self.is_connected:
            await self.connect()

        async def preprocess_handler(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"Received preprocess request for document: {data.get('document_id')}")
            # Placeholder for actual preprocessing logic
            # For now, just acknowledge or publish a dummy result
            await self.nc.publish("document.preprocessed", json.dumps({"status": "ok", "document_id": data.get("document_id")}).encode())

        await self.nc.subscribe("document.preprocess", cb=preprocess_handler)
        logger.info("Subscribed to document.preprocess")

# Global NATS handler instance
nats_handler = NatsHandler()

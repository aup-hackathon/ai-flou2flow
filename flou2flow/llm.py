"""Local-only LLM client supporting Ollama."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)

# Type alias: callers pass the Pydantic *class* (not an instance)
SchemaType = type[BaseModel] | None


class LLMClient:
    """Strictly Local LLM client for Ollama."""

    def __init__(self):
        self.model = settings.LLM_MODEL
        self.client = httpx.AsyncClient(timeout=300.0)

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = True,
        model: str | None = None,
        response_schema: SchemaType = None,
    ) -> str:
        """Call Ollama local API."""
        temp = temperature or settings.TEMPERATURE
        tokens = max_tokens or settings.MAX_TOKENS
        target_model = model or self.model

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": tokens,
            },
        }

        if response_schema is not None:
            # Pro Method: Native Schema Enforcement
            schema = response_schema.model_json_schema()
            logger.info(f"Using structured output schema: {response_schema.__name__}")
            payload["format"] = schema
        elif json_mode:
            payload["format"] = "json"

        logger.info(f"Calling Ollama with model={target_model}")

        response = await self.client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data["message"]["content"]
        logger.info(f"Ollama response received ({len(content)} chars)")
        return content

    async def vision_chat(
        self,
        prompt: str,
        image_data: str, # Base64
        model: str | None = None,
    ) -> str:
        """Analyze an image locally using a vision model (like moondream)."""
        target_model = model or settings.VISION_MODEL

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_data]
                }
            ],
            "stream": False,
        }

        logger.info(f"Calling Ollama Vision with model={target_model}")
        response = await self.client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    def parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = response.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            try:
                first_newline = text.index("\n")
                text = text[first_newline + 1:]
            except ValueError:
                text = text[3:]

            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError as inner_e:
                    raise ValueError(f"Could not parse JSON from LLM response: {inner_e}")
            raise ValueError("Could not parse JSON from LLM response")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
llm_client = LLMClient()

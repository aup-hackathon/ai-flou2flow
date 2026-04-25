"""Local-only LLM client with Self-Healing JSON parsing for tiny models."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from pydantic import BaseModel

from .config import settings

logger = logging.getLogger(__name__)

# Type alias: callers pass the Pydantic *class* (not an instance)
SchemaType = type[BaseModel] | None


class LLMClient:
    """Strictly Local LLM client with built-in JSON repair."""

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
        """Call Ollama /api/generate."""
        temp = temperature or settings.TEMPERATURE
        tokens = max_tokens or settings.MAX_TOKENS
        target_model = model or self.model

        # Optimized combined prompt
        full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"

        payload: dict[str, Any] = {
            "model": target_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": tokens,
            },
        }

        logger.info(f"Calling Ollama /api/generate with model={target_model}")

        response = await self.client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data["response"]
        logger.info(f"Ollama response received ({len(content)} chars)")
        return content

    def parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response with Self-Healing logic."""
        text = response.strip()

        # 1. Basic Cleaning
        if text.startswith("```"):
            try:
                first_newline = text.index("\n")
                text = text[first_newline + 1:]
            except ValueError:
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3].strip()

        # 2. Extract first {...} if there is conversational noise
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        # 3. Self-Healing: Fix trailing commas (common in tiny models)
        # Matches a comma followed by closing brace/bracket with optional whitespace
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        # 4. Self-Healing: Fix unquoted keys if necessary (basic attempt)
        # text = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse failed: {e}. Raw: {text[:200]}...")
            raise ValueError(f"Could not parse JSON from LLM response: {e}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
llm_client = LLMClient()

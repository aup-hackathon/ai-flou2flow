"""LLM client supporting Mistral AI API and Ollama."""

from __future__ import annotations

import json
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client for Mistral API and Ollama."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
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
    ) -> str:
        """Send a chat completion request and return the response text."""
        temp = temperature or settings.TEMPERATURE
        tokens = max_tokens or settings.MAX_TOKENS

        target_model = model or self.model
        if self.provider == "ollama":
            return await self._ollama_chat(system_prompt, user_prompt, temp, tokens, json_mode, target_model)
        else:
            return await self._mistral_chat(system_prompt, user_prompt, temp, tokens, json_mode, target_model)

    async def _mistral_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        model: str,
    ) -> str:
        """Call Mistral AI API."""
        headers = {
            "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        logger.info(f"Calling Mistral API with model={model}")

        response = await self.client.post(
            settings.MISTRAL_API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        logger.info(f"Mistral API response received ({len(content)} chars)")
        return content

    async def _ollama_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        model: str,
    ) -> str:
        """Call Ollama local API."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        if json_mode:
            payload["format"] = "json"

        logger.info(f"Calling Ollama with model={model}")

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
        """Analyze an image using a vision model."""
        target_model = model or settings.VISION_MODEL

        if self.provider == "ollama":
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
        else:
            # Fallback or Mistral multimodal if supported
            logger.warning("Vision chat not fully implemented for non-ollama providers")
            return "Vision analysis currently only supported with Ollama provider."

    def parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = response.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            # Remove opening ```json or ```
            first_newline = text.index("\n")
            text = text[first_newline + 1:]
            # Remove closing ```
            if text.endswith("```"):
                text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {text[:500]}")
            # Try to find JSON in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from LLM response: {e}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
llm_client = LLMClient()

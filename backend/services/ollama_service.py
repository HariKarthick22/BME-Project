"""
backend/services/ollama_service.py
Async Ollama client for MedGemma 1.5 4B — supports text and multimodal (X-ray/image) inputs.
"""

import base64
import json
import logging
from typing import AsyncGenerator, Optional

import httpx

logger = logging.getLogger(__name__)


class OllamaService:
    """Async client for Ollama API, optimised for MedGemma multimodal inference."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "medgemma:4b",
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _build_messages(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> list[dict]:
        """Prepend system prompt if provided."""
        if system_prompt:
            return [{"role": "system", "content": system_prompt}] + messages
        return messages

    async def generate_stream(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream tokens from Ollama as they are generated.

        Args:
            messages: List of {"role": "user"/"assistant", "content": str | list}
                      For image inputs, content is a list with text + image parts.
            system_prompt: Optional system prompt prepended to the conversation.

        Yields:
            Individual token strings as they arrive.
        """
        payload = {
            "model": self.model,
            "messages": self._build_messages(messages, system_prompt),
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
            except httpx.ConnectError:
                logger.error("Cannot connect to Ollama at %s — is it running?", self.base_url)
                yield "⚠️ CarePath AI is offline. Please start Ollama: `ollama serve`"
            except httpx.TimeoutException:
                logger.error("Ollama request timed out after %ss", self.timeout)
                yield "⚠️ The request timed out. Please try again with a shorter message."

    async def generate(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate a complete (non-streaming) response from Ollama.

        Returns the full response text as a single string.
        """
        tokens = []
        async for token in self.generate_stream(messages, system_prompt):
            tokens.append(token)
        return "".join(tokens)

    async def generate_with_image(
        self,
        text_prompt: str,
        image_bytes: bytes,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a multimodal response for X-ray / medical image analysis.

        Encodes the image as base64 and passes it as an Ollama image attachment.
        MedGemma 1.5 4B supports MIMIC-CXR chest X-ray analysis natively.

        Args:
            text_prompt: Text instruction (e.g., "Analyze this chest X-ray")
            image_bytes: Raw image bytes (JPEG/PNG/WebP)
            system_prompt: Optional system prompt

        Yields:
            Individual token strings.
        """
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": text_prompt,
                "images": [image_b64],
            }
        ]

        async for token in self.generate_stream(messages, system_prompt):
            yield token

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False
                models = response.json().get("models", [])
                return any(self.model in m.get("name", "") for m in models)
        except Exception:
            return False

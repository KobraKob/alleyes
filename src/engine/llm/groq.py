"""Groq API implementation of the LLMClient protocol."""

import contextlib
import json
import logging
from typing import Any

import httpx

from src.engine.config import get_settings
from src.engine.llm.client import LLMResponse

logger = logging.getLogger(__name__)


class GroqLLMClient:
    """Production LLM client wrapping Groq OpenAI-compatible Chat Completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.groq_api_key
        self.default_model = default_model or settings.llm_model or "openai/gpt-oss-120b"
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your environment or .env file."
            )

        selected_model = model or self.default_model

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as e:
            # If json_object mode fails (some models or endpoints), retry without response_format
            if e.response.status_code == 400 and "response_format" in str(e.response.text):
                payload.pop("response_format", None)
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
            else:
                logger.error("Groq API error: %s - %s", e.response.status_code, e.response.text)
                raise RuntimeError(
                    f"Groq API error {e.response.status_code}: {e.response.text}"
                ) from e
        except Exception as e:
            logger.error("Groq connection failure: %s", e)
            raise RuntimeError(f"Groq request failed: {e}") from e

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        text_content = str(message.get("content", "") or "")
        tool_calls = message.get("tool_calls")

        usage = data.get("usage", {})
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))

        structured_data = None
        with contextlib.suppress(Exception):
            structured_data = json.loads(text_content)

        return LLMResponse(
            content=text_content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_calls=tool_calls,
            structured_data=structured_data,
        )

"""Anthropic SDK implementation of the LLMClient protocol."""

import contextlib
import json
from typing import Any

import anthropic

from src.engine.config import get_settings
from src.engine.llm.client import LLMResponse

settings = get_settings()


class AnthropicLLMClient:
    """Production LLM client wrapping Anthropic Python SDK."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self.default_model = default_model or settings.llm_model
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        if not self.client:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        selected_model = model or self.default_model

        kwargs: dict[str, Any] = {
            "model": selected_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        text_content = ""
        for block in response.content:
            if hasattr(block, "text"):
                text_content += block.text

        structured_data = None
        with contextlib.suppress(Exception):
            structured_data = json.loads(text_content)

        return LLMResponse(
            content=text_content,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            structured_data=structured_data,
        )

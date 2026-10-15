"""LLM client protocol and structured output schemas."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tokens_in: int
    tokens_out: int
    tool_calls: list[dict[str, Any]] | None = None
    structured_data: dict[str, Any] | None = None


@runtime_checkable
class LLMClient(Protocol):
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...

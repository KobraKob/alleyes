"""LLM, client abstractions, tracing, and client factory."""

from src.engine.config import get_settings
from src.engine.llm.anthropic import AnthropicLLMClient
from src.engine.llm.client import LLMClient, LLMResponse
from src.engine.llm.fake import FakeLLMClient
from src.engine.llm.groq import GroqLLMClient
from src.engine.llm.tracing import record_agent_run_finish, record_agent_run_start


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory creating configured LLM client instance."""
    settings = get_settings()
    p = (provider or settings.llm_provider or "groq").lower()
    if p == "groq":
        return GroqLLMClient()
    elif p == "anthropic":
        return AnthropicLLMClient()
    elif p == "fake":
        return FakeLLMClient()
    return GroqLLMClient()


__all__ = [
    "LLMClient",
    "LLMResponse",
    "FakeLLMClient",
    "AnthropicLLMClient",
    "GroqLLMClient",
    "get_llm_client",
    "record_agent_run_start",
    "record_agent_run_finish",
]

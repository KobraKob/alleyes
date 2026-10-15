"""Agent execution runtime enforcing capabilities, timeouts, token budgets, and structured output retries."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from src.engine.llm.client import LLMClient, LLMResponse

T = TypeVar("T", bound=BaseModel)


@dataclass
class AgentContext:
    business_id: UUID
    run_id: UUID
    session: Session
    llm: LLMClient
    pack_config: dict[str, Any] = field(default_factory=dict)
    brand_profile: dict[str, Any] = field(default_factory=dict)


def load_prompt_file(relative_path: str) -> tuple[str, str]:
    """
    Loads markdown prompt file from prompts/ directory.
    Returns (prompt_text, version_header).
    """
    base_dir = Path(__file__).parent.parent.parent.parent / "prompts"
    prompt_path = base_dir / relative_path
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    version = "1.0.0"
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            header = parts[1]
            body = parts[2].strip()
            for line in header.splitlines():
                if line.strip().startswith("version:"):
                    version = line.split(":", 1)[1].strip().strip('"').strip("'")
            content = f"/* {header.strip()} */\n\n{body}"

    return content, version


def execute_structured_completion(
    llm: LLMClient,
    prompt: str,
    system_prompt: str,
    output_schema: type[T],
    max_retries: int = 1,
) -> tuple[T, int, int]:
    """
    Executes an LLM completion expecting JSON matching output_schema.
    Retries once with validation error details on failure.
    Returns (parsed_model, tokens_in, tokens_out).
    """
    tokens_in_total = 0
    tokens_out_total = 0

    curr_prompt = prompt
    for attempt in range(max_retries + 1):
        resp: LLMResponse = llm.complete(
            prompt=curr_prompt,
            system=system_prompt,
        )
        tokens_in_total += resp.tokens_in
        tokens_out_total += resp.tokens_out

        try:
            # Check if structured data is already present or parse content
            raw_dict = resp.structured_data
            if raw_dict is None:
                raw_dict = json.loads(resp.content)
            parsed = output_schema.model_validate(raw_dict)
            return parsed, tokens_in_total, tokens_out_total
        except (json.JSONDecodeError, ValidationError) as err:
            if attempt == max_retries:
                raise RuntimeError(
                    f"Agent failed structured output validation after {max_retries + 1} attempts: {err}"
                ) from err
            # Format retry prompt
            curr_prompt = f"{prompt}\n\nPREVIOUS ATTEMPT FAILED SCHEMA VALIDATION:\n{err}\nPlease return ONLY valid JSON matching the schema."

    raise RuntimeError("Unexpected structured completion exit.")

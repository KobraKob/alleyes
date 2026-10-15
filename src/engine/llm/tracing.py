"""Execution tracing and audit logging for agent LLM calls."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.config import get_settings

settings = get_settings()


def record_agent_run_start(
    session: Session,
    business_id: UUID,
    agent_name: str,
    trigger: str,
    objective_id: UUID | None = None,
    model_name: str | None = None,
) -> UUID:
    """Creates a new agent_runs record in 'running' state."""
    run_id = uuid4()
    session.execute(
        text("""
            INSERT INTO agent_runs (
                id, business_id, agent, trigger, objective_id, model, started_at, status
            )
            VALUES (
                :id, :biz_id, :agent, :trigger, :obj_id, :model, now(), 'running'
            )
        """),
        {
            "id": str(run_id),
            "biz_id": str(business_id),
            "agent": agent_name,
            "trigger": trigger,
            "obj_id": str(objective_id) if objective_id else None,
            "model": model_name or settings.llm_model,
        },
    )
    return run_id


def record_agent_run_finish(
    session: Session,
    business_id: UUID,
    run_id: UUID,
    status: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_minor: int = 0,
    trace_data: dict[str, Any] | None = None,
) -> str:
    """Updates agent_runs record with token usage and persists trace payload."""
    trace_uri = f"{settings.trace_store_uri}/trace_{run_id}.json"

    # Persist trace data to local directory if using file://
    if settings.trace_store_uri.startswith("file://") and trace_data:
        dir_path = Path(settings.trace_store_uri.replace("file://", ""))
        dir_path.mkdir(parents=True, exist_ok=True)
        trace_file = dir_path / f"trace_{run_id}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, indent=2)

    session.execute(
        text("""
            UPDATE agent_runs
            SET status = :status,
                finished_at = now(),
                tokens_in = :t_in,
                tokens_out = :t_out,
                cost_minor = :cost,
                trace_uri = :uri
            WHERE business_id = :biz_id AND id = :run_id
        """),
        {
            "status": status,
            "t_in": tokens_in,
            "t_out": tokens_out,
            "cost": cost_minor,
            "uri": trace_uri,
            "biz_id": str(business_id),
            "run_id": str(run_id),
        },
    )
    return trace_uri

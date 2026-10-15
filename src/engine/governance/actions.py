"""Action proposal and action records."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ActionRecord:
    id: UUID
    business_id: UUID
    kind: str
    payload: dict[str, Any]
    risk_tier: int
    requires_approval: bool
    status: str
    reasoning: str | None
    idempotency_key: str
    proposed_at: datetime
    run_id: UUID | None = None
    executed_at: datetime | None = None
    external_ref: str | None = None
    error: str | None = None


def propose_action(
    session: Session,
    *,
    business_id: UUID,
    kind: str,
    payload: dict[str, Any],
    reasoning: str | None,
    risk_tier: int = 1,
    idempotency_key: str,
    run_id: UUID | None = None,
) -> ActionRecord:
    """
    Inserts a proposed action into the actions table with ON CONFLICT DO NOTHING.
    Returns the action record.
    """
    action_id = uuid4()
    proposed_at = datetime.now(UTC)

    # Check if already exists for idempotency
    existing = session.execute(
        text("""
            SELECT id, kind, payload, risk_tier, requires_approval, status,
                   reasoning, idempotency_key, proposed_at, run_id, executed_at,
                   external_ref, error
            FROM actions
            WHERE business_id = :biz_id AND idempotency_key = :idemp_key
        """),
        {"biz_id": str(business_id), "idemp_key": idempotency_key},
    ).fetchone()

    if existing:
        return ActionRecord(
            id=UUID(str(existing[0])),
            business_id=business_id,
            kind=str(existing[1]),
            payload=existing[2]
            if isinstance(existing[2], dict)
            else json.loads(existing[2] or "{}"),
            risk_tier=int(existing[3]),
            requires_approval=bool(existing[4]),
            status=str(existing[5]),
            reasoning=str(existing[6]) if existing[6] else None,
            idempotency_key=str(existing[7]),
            proposed_at=existing[8],
            run_id=UUID(str(existing[9])) if existing[9] else None,
            executed_at=existing[10],
            external_ref=str(existing[11]) if existing[11] else None,
            error=str(existing[12]) if existing[12] else None,
        )

    # Insert proposed action
    session.execute(
        text("""
            INSERT INTO actions (
                id, business_id, run_id, kind, payload, risk_tier,
                requires_approval, status, reasoning, idempotency_key, proposed_at
            )
            VALUES (
                :id, :biz_id, :run_id, :kind, :payload, :risk_tier,
                true, 'proposed', :reasoning, :idemp_key, :proposed_at
            )
        """),
        {
            "id": str(action_id),
            "biz_id": str(business_id),
            "run_id": str(run_id) if run_id else None,
            "kind": kind,
            "payload": json.dumps(payload),
            "risk_tier": risk_tier,
            "reasoning": reasoning,
            "idemp_key": idempotency_key,
            "proposed_at": proposed_at,
        },
    )

    return ActionRecord(
        id=action_id,
        business_id=business_id,
        kind=kind,
        payload=payload,
        risk_tier=risk_tier,
        requires_approval=True,
        status="proposed",
        reasoning=reasoning,
        idempotency_key=idempotency_key,
        proposed_at=proposed_at,
        run_id=run_id,
    )

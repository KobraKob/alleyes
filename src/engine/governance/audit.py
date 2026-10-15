"""Append-only audit log writer and integrity guards."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def write_audit_log(
    session: Session,
    business_id: UUID | None,
    actor_kind: str,
    actor_id: str | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    diff: dict[str, Any] | None = None,
) -> None:
    """Inserts an immutable audit log record."""
    session.execute(
        text("""
            INSERT INTO audit_log (
                business_id, actor_kind, actor_id, action, entity_type, entity_id, diff, at
            )
            VALUES (
                :biz_id, :actor_kind, :actor_id, :action, :entity_type, :entity_id, :diff, now()
            )
        """),
        {
            "biz_id": str(business_id) if business_id else None,
            "actor_kind": actor_kind,
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "diff": json.dumps(diff) if diff else None,
        },
    )

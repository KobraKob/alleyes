"""Human approval and action modification queue."""

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.governance.executor import execute_action


def list_pending_approvals(session: Session, business_id: UUID) -> list[dict[str, Any]]:
    """Retrieves all proposed actions awaiting human review."""
    rows = session.execute(
        text("""
            SELECT id, kind, payload, risk_tier, reasoning, policy_results, proposed_at
            FROM actions
            WHERE business_id = :biz_id AND status = 'proposed' AND requires_approval = true
            ORDER BY proposed_at ASC
        """),
        {"biz_id": str(business_id)},
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "kind": str(r[1]),
            "payload": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
            "risk_tier": int(r[3]),
            "reasoning": str(r[4]) if r[4] else None,
            "policy_results": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
            "proposed_at": r[6].isoformat() if r[6] else None,
        }
        for r in rows
    ]


def submit_approval(
    session: Session,
    business_id: UUID,
    action_id: UUID,
    approver_id: UUID,
    decision: str,  # 'approved', 'rejected', 'edited'
    comment: str | None = None,
    edited_payload: dict[str, Any] | None = None,
    override_connector: Any | None = None,
) -> dict[str, Any]:
    """Processes a human approval decision and triggers execution if approved."""
    if decision not in ("approved", "rejected", "edited"):
        raise ValueError(f"Invalid approval decision: {decision}")

    # Record in approvals table
    session.execute(
        text("""
            INSERT INTO approvals (
                id, business_id, action_id, approver_id, decision, comment, edited_payload, decided_at
            )
            VALUES (
                :id, :biz_id, :act_id, :appr_id, :dec, :comm, :ed_payload, now()
            )
        """),
        {
            "id": str(uuid4()),
            "biz_id": str(business_id),
            "act_id": str(action_id),
            "appr_id": str(approver_id),
            "dec": decision,
            "comm": comment,
            "ed_payload": json.dumps(edited_payload) if edited_payload else None,
        },
    )

    if decision == "rejected":
        session.execute(
            text("""
                UPDATE actions
                SET status = 'rejected',
                    requires_approval = false,
                    error = :err
                WHERE business_id = :biz_id AND id = :act_id
            """),
            {
                "err": f"Rejected by user: {comment or 'No comment'}",
                "biz_id": str(business_id),
                "act_id": str(action_id),
            },
        )
        return {"status": "rejected", "action_id": str(action_id)}

    elif decision == "edited" and edited_payload:
        session.execute(
            text("""
                UPDATE actions
                SET payload = :new_payload,
                    status = 'approved',
                    requires_approval = false
                WHERE business_id = :biz_id AND id = :act_id
            """),
            {
                "new_payload": json.dumps(edited_payload),
                "biz_id": str(business_id),
                "act_id": str(action_id),
            },
        )

    elif decision == "approved":
        session.execute(
            text("""
                UPDATE actions
                SET status = 'approved',
                    requires_approval = false
                WHERE business_id = :biz_id AND id = :act_id
            """),
            {"biz_id": str(business_id), "act_id": str(action_id)},
        )

    # Now execute the approved/edited action
    res = execute_action(
        session=session,
        business_id=business_id,
        action_id=action_id,
        override_connector=override_connector,
    )
    return res

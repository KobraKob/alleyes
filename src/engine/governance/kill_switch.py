"""Kill switch control service."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_kill_switch(
    session: Session,
    business_id: UUID,
    scope: str = "all",
    engaged: bool = True,
    user_id: UUID | None = None,
    reason: str | None = None,
) -> None:
    """Engages or disengages a kill switch for a business and scope."""
    session.execute(
        text("""
            INSERT INTO kill_switches (business_id, scope, engaged, engaged_by, reason, changed_at)
            VALUES (:biz_id, :scope, :engaged, :user_id, :reason, now())
            ON CONFLICT (business_id, scope) DO UPDATE
            SET engaged = EXCLUDED.engaged,
                engaged_by = EXCLUDED.engaged_by,
                reason = EXCLUDED.reason,
                changed_at = now()
        """),
        {
            "biz_id": str(business_id),
            "scope": scope,
            "engaged": engaged,
            "user_id": str(user_id) if user_id else None,
            "reason": reason,
        },
    )

    # If engaged, cancel/block currently proposed and approved unexecuted sends
    if engaged:
        session.execute(
            text("""
                UPDATE actions
                SET status = 'rejected',
                    error = 'Cancelled by kill switch engagement'
                WHERE business_id = :biz_id
                  AND status IN ('proposed', 'approved')
                  AND (kind = 'send_message' OR :scope = 'all' OR kind = :scope)
            """),
            {"biz_id": str(business_id), "scope": scope},
        )


def is_kill_switch_engaged(
    session: Session,
    business_id: UUID,
    scope: str = "all",
) -> bool:
    """Checks if a kill switch is active (global 'all' or specific scope)."""
    row = session.execute(
        text("""
            SELECT engaged FROM kill_switches
            WHERE business_id = :biz_id AND scope IN ('all', :scope) AND engaged = true
            LIMIT 1
        """),
        {"biz_id": str(business_id), "scope": scope},
    ).fetchone()

    return bool(row and row[0])

"""Reporting, campaign performance, and qualitative insights router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from src.engine.db.session import tenant_session

router = APIRouter(prefix="/v1", tags=["reports"])


@router.get("/reports/campaigns")
def get_campaigns_performance(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[dict[str, Any]]:
    """Fetches campaign performance from v_campaign_reward_per_rupee view."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        rows = session.execute(
            text("""
                SELECT campaign_id, name, reward, spend_minor, reward_per_rupee
                FROM v_campaign_reward_per_rupee
                WHERE business_id = :b
            """),
            {"b": str(biz_id)},
        ).fetchall()

        return [
            {
                "campaign_id": str(r[0]),
                "name": r[1],
                "reward": float(r[2]),
                "spend_minor": int(r[3]),
                "reward_per_rupee": float(r[4]) if r[4] is not None else 0.0,
            }
            for r in rows
        ]


@router.get("/reports/weekly")
def get_weekly_funnel_summary(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Summary of contacts, conversions, and speed-to-lead."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        # Funnel stage counts
        stage_counts = session.execute(
            text("""
                SELECT s.key, COUNT(c.id) FROM funnel_stages s
                LEFT JOIN contact_stage_history c ON c.stage_id = s.id AND c.business_id = :b
                WHERE s.business_id = :b
                GROUP BY s.key, s.ordinal
                ORDER BY s.ordinal ASC
            """),
            {"b": str(biz_id)},
        ).fetchall()

        # Average response time
        sla_row = session.execute(
            text("SELECT AVG(first_response_seconds) FROM conversations WHERE business_id = :b"),
            {"b": str(biz_id)},
        ).fetchone()
        avg_sla = float(sla_row[0]) if (sla_row and sla_row[0] is not None) else 0.0

        return {
            "funnel": {r[0]: int(r[1]) for r in stage_counts},
            "avg_first_response_seconds": round(avg_sla, 1),
        }


@router.get("/insights")
def list_playbook_insights(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[dict[str, Any]]:
    """Lists current qualitative playbook insights."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        rows = session.execute(
            text("""
                SELECT id, statement, evidence, confidence, status, expires_at, created_at
                FROM playbook_insights
                WHERE business_id = :b
                ORDER BY confidence DESC, created_at DESC
            """),
            {"b": str(biz_id)},
        ).fetchall()

        return [
            {
                "id": str(r[0]),
                "statement": r[1],
                "evidence": r[2],
                "confidence": float(r[3]),
                "status": r[4],
                "expires_at": r[5].isoformat() if r[5] else None,
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]

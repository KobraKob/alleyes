"""Business entities, objectives, decisions introspection, and PII erasure router."""

import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from src.engine.db.session import tenant_session
from src.engine.identity.resolution import erase_contact_pii

router = APIRouter(prefix="/v1", tags=["businesses"])


class CreateObjectiveRequest(BaseModel):
    statement: str
    target_value: float
    budget_minor: int
    period_start: str
    period_end: str
    location_id: UUID | None = None
    target_stage_id: UUID | None = None
    constraints: dict[str, Any] = {}


@router.get("/businesses")
def get_business_details(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        row = session.execute(
            text(
                "SELECT id, name, timezone, currency, brand_profile, status FROM businesses WHERE id = :b"
            ),
            {"b": str(biz_id)},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Business not found.")
        return {
            "id": str(row[0]),
            "name": row[1],
            "timezone": row[2],
            "currency": row[3],
            "brand_profile": row[4],
            "status": row[5],
        }


@router.get("/locations")
def list_locations(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[dict[str, Any]]:
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        rows = session.execute(
            text(
                "SELECT id, name, city, capacity_per_day, catchment_m FROM locations WHERE business_id = :b"
            ),
            {"b": str(biz_id)},
        ).fetchall()
        return [
            {"id": str(r[0]), "name": r[1], "city": r[2], "capacity": r[3], "catchment_m": r[4]}
            for r in rows
        ]


@router.get("/objectives")
def list_objectives(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[dict[str, Any]]:
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        rows = session.execute(
            text(
                "SELECT id, statement, target_value, budget_minor, constraints, status FROM objectives WHERE business_id = :b"
            ),
            {"b": str(biz_id)},
        ).fetchall()
        return [
            {
                "id": str(r[0]),
                "statement": r[1],
                "target_value": float(r[2]),
                "budget_minor": int(r[3]),
                "constraints": r[4],
                "status": r[5],
            }
            for r in rows
        ]


@router.post("/objectives")
def create_objective(
    req: CreateObjectiveRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, str]:
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)
    obj_id = uuid4()

    with tenant_session(biz_id) as session:
        session.execute(
            text("""
                INSERT INTO objectives (
                    id, business_id, location_id, statement, target_stage, target_value,
                    period, budget_minor, constraints, status, created_at
                )
                VALUES (
                    :id, :biz_id, :loc_id, :stmt, :stage_id, :val,
                    daterange(:p_start::date, :p_end::date, '[]'),
                    :budget, :constraints, 'active', now()
                )
            """),
            {
                "id": str(obj_id),
                "biz_id": str(biz_id),
                "loc_id": str(req.location_id) if req.location_id else None,
                "stmt": req.statement,
                "stage_id": str(req.target_stage_id) if req.target_stage_id else None,
                "val": req.target_value,
                "p_start": req.period_start,
                "p_end": req.period_end,
                "budget": req.budget_minor,
                "constraints": json.dumps(req.constraints),
            },
        )

    return {"id": str(obj_id), "status": "active"}


@router.get("/decisions/{decision_id}")
def get_decision_explanation(
    decision_id: UUID,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Introspects a decision: candidate arms, chosen arm, propensity, context, and rewards."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        dec_row = session.execute(
            text("""
                SELECT d.id, d.chosen_arm_id, d.candidate_arm_ids, d.propensity,
                       d.explored, d.policy_version, d.context, d.decided_at,
                       a.label AS chosen_arm_label, a.signature AS chosen_arm_sig
                FROM decisions d
                JOIN arms a ON a.id = d.chosen_arm_id
                WHERE d.business_id = :biz_id AND d.id = :dec_id
            """),
            {"biz_id": str(biz_id), "dec_id": str(decision_id)},
        ).fetchone()

        if not dec_row:
            raise HTTPException(status_code=404, detail="Decision not found.")

        # Fetch candidate arm labels
        candidates = dec_row[2] or []
        candidate_labels = {}
        if candidates:
            c_rows = session.execute(
                text("SELECT id, label, signature FROM arms WHERE id = ANY(:c_ids)"),
                {"c_ids": [str(c) for c in candidates]},
            ).fetchall()
            candidate_labels = {str(r[0]): {"label": r[1], "signature": r[2]} for r in c_rows}

        # Fetch reward snapshots
        reward_rows = session.execute(
            text("""
                SELECT kind, value, components, is_final, observed_at
                FROM rewards
                WHERE decision_id = :dec_id
                ORDER BY observed_at ASC
            """),
            {"dec_id": str(decision_id)},
        ).fetchall()

        rewards_list = [
            {
                "kind": r[0],
                "value": float(r[1]),
                "components": r[2],
                "is_final": bool(r[3]),
                "observed_at": r[4].isoformat() if r[4] else None,
            }
            for r in reward_rows
        ]

        return {
            "id": str(dec_row[0]),
            "chosen_arm_id": str(dec_row[1]),
            "chosen_arm_label": dec_row[8],
            "chosen_arm_signature": dec_row[9],
            "propensity": float(dec_row[3]),
            "explored": bool(dec_row[4]),
            "policy_version": dec_row[5],
            "context": dec_row[6],
            "decided_at": dec_row[7].isoformat() if dec_row[7] else None,
            "candidates": candidate_labels,
            "reward_history": rewards_list,
        }


@router.delete("/contacts/{contact_id}/pii")
def erase_contact_endpoint(
    contact_id: UUID,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, str]:
    """DPDP-compliant hard erasure of personal data."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    biz_id = UUID(x_business_id)

    with tenant_session(biz_id) as session:
        erase_contact_pii(session, biz_id, contact_id)

    return {"status": "erased", "contact_id": str(contact_id)}

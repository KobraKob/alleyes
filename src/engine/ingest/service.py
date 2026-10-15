"""Event ingestion and funnel stage progression service."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session


class IngestEventItem(BaseModel):
    event_type: str
    occurred_at: datetime
    idempotency_key: str
    source: str = "api"
    contact_id: UUID | None = None
    anonymous_id: str | None = None
    location_id: UUID | None = None
    campaign_id: UUID | None = None
    asset_id: UUID | None = None
    decision_id: UUID | None = None
    tracking_code: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    value_minor: int | None = None


class IngestEventResponse(BaseModel):
    idempotency_key: str
    status: str  # 'inserted', 'duplicate', 'invalid'
    error: str | None = None


def process_event_batch(
    session: Session,
    business_id: UUID,
    events: list[IngestEventItem],
) -> list[IngestEventResponse]:
    """
    Ingests up to 500 events in a batch.
    Validates against event_types, handles ON CONFLICT DO NOTHING idempotently,
    and advances funnel stages for conversion events.
    """
    if len(events) > 500:
        raise ValueError("Batch limit exceeded: maximum 500 events per request.")

    # 1. Fetch valid event types
    rows = session.execute(text("SELECT key, stage_key FROM event_types")).fetchall()
    valid_types = {r[0]: r[1] for r in rows}

    responses: list[IngestEventResponse] = []

    for ev in events:
        if ev.event_type not in valid_types:
            responses.append(
                IngestEventResponse(
                    idempotency_key=ev.idempotency_key,
                    status="invalid",
                    error=f"Unrecognized event_type: {ev.event_type}",
                )
            )
            continue

        stage_key = valid_types[ev.event_type]
        event_id = uuid4()

        # Check tracking link if tracking_code provided and campaign_id is not
        campaign_id = ev.campaign_id
        asset_id = ev.asset_id
        location_id = ev.location_id

        if ev.tracking_code and not campaign_id:
            link_row = session.execute(
                text("""
                    SELECT campaign_id, asset_id, location_id FROM tracking_links
                    WHERE business_id = :biz_id AND code = :code
                """),
                {"biz_id": str(business_id), "code": ev.tracking_code},
            ).fetchone()
            if link_row:
                campaign_id = UUID(str(link_row[0])) if link_row[0] else None
                asset_id = UUID(str(link_row[1])) if link_row[1] else asset_id
                location_id = UUID(str(link_row[2])) if link_row[2] else location_id

        # Insert into events table with ON CONFLICT DO NOTHING
        insert_sql = text("""
            INSERT INTO events (
                id, business_id, event_type, occurred_at, recorded_at,
                contact_id, anonymous_id, location_id, campaign_id, asset_id,
                decision_id, tracking_code, source, properties, value_minor, idempotency_key
            )
            VALUES (
                :id, :biz_id, :event_type, :occurred_at, now(),
                :contact_id, :anon_id, :loc_id, :camp_id, :asset_id,
                :decision_id, :tracking_code, :source, :props, :val_minor, :idemp_key
            )
            ON CONFLICT (business_id, idempotency_key, occurred_at) DO NOTHING
            RETURNING id;
        """)

        result = session.execute(
            insert_sql,
            {
                "id": str(event_id),
                "biz_id": str(business_id),
                "event_type": ev.event_type,
                "occurred_at": ev.occurred_at,
                "contact_id": str(ev.contact_id) if ev.contact_id else None,
                "anon_id": ev.anonymous_id,
                "loc_id": str(location_id) if location_id else None,
                "camp_id": str(campaign_id) if campaign_id else None,
                "asset_id": str(asset_id) if asset_id else None,
                "decision_id": str(ev.decision_id) if ev.decision_id else None,
                "tracking_code": ev.tracking_code,
                "source": ev.source,
                "props": json.dumps(ev.properties),
                "val_minor": ev.value_minor,
                "idemp_key": ev.idempotency_key,
            },
        ).fetchone()

        if not result:
            responses.append(
                IngestEventResponse(idempotency_key=ev.idempotency_key, status="duplicate")
            )
            continue

        responses.append(IngestEventResponse(idempotency_key=ev.idempotency_key, status="inserted"))

        # Funnel stage derivation: advance funnel stages and record conversion
        if stage_key and ev.contact_id:
            advance_funnel_stage(
                session=session,
                business_id=business_id,
                contact_id=ev.contact_id,
                stage_key=stage_key,
                occurred_at=ev.occurred_at,
                source_event_id=event_id,
                value_minor=ev.value_minor or 0,
            )

    return responses


def advance_funnel_stage(
    session: Session,
    business_id: UUID,
    contact_id: UUID,
    stage_key: str,
    occurred_at: datetime,
    source_event_id: UUID,
    value_minor: int = 0,
) -> None:
    """
    Finds the funnel stage by key. If the contact has not reached this stage,
    inserts contact_stage_history and conversions records.
    Stages only advance.
    """
    stage_row = session.execute(
        text("SELECT id FROM funnel_stages WHERE business_id = :biz_id AND key = :key"),
        {"biz_id": str(business_id), "key": stage_key},
    ).fetchone()

    if not stage_row:
        return

    stage_id = UUID(str(stage_row[0]))

    # Insert stage history
    session.execute(
        text("""
            INSERT INTO contact_stage_history (id, business_id, contact_id, stage_id, entered_at, source_event_id)
            VALUES (:id, :biz_id, :contact_id, :stage_id, :entered_at, :src_ev_id)
            ON CONFLICT (contact_id, stage_id) DO NOTHING
        """),
        {
            "id": str(uuid4()),
            "biz_id": str(business_id),
            "contact_id": str(contact_id),
            "stage_id": str(stage_id),
            "entered_at": occurred_at,
            "src_ev_id": str(source_event_id),
        },
    )

    # Insert conversion
    session.execute(
        text("""
            INSERT INTO conversions (
                id, business_id, contact_id, stage_id, occurred_at, value_minor, verified, source_event_id
            )
            VALUES (
                :id, :biz_id, :contact_id, :stage_id, :occurred_at, :val_minor, true, :src_ev_id
            )
            ON CONFLICT (contact_id, stage_id) DO NOTHING
        """),
        {
            "id": str(uuid4()),
            "biz_id": str(business_id),
            "contact_id": str(contact_id),
            "stage_id": str(stage_id),
            "occurred_at": occurred_at,
            "val_minor": value_minor,
            "src_ev_id": str(source_event_id),
        },
    )

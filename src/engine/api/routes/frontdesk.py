"""Front-desk walk-in event logging API."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.engine.db.session import tenant_session
from src.engine.identity.resolution import upsert_contact_by_identifier
from src.engine.ingest.service import IngestEventItem, process_event_batch

router = APIRouter(prefix="/v1/frontdesk", tags=["frontdesk"])


class FrontDeskEventRequest(BaseModel):
    phone: str
    full_name: str | None = None
    source_reported: str  # e.g. "Instagram Ad", "Friend referral", "Walkby billboard"
    event_type: str = (
        "trial.attended"  # 'frontdesk.source_reported', 'trial.attended', 'membership.purchased'
    )
    tracking_code: str | None = None
    location_id: UUID | None = None
    value_minor: int | None = None


@router.post("/events")
def log_frontdesk_event(
    req: FrontDeskEventRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, str]:
    """Logs front-desk walk-in source report and conversion events."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    now = datetime.now(UTC)

    with tenant_session(biz_id) as session:
        # 1. Upsert contact
        contact_id = upsert_contact_by_identifier(
            session=session,
            business_id=biz_id,
            identifier_type="phone",
            raw_value=req.phone,
            full_name=req.full_name,
            phone=req.phone,
            location_id=req.location_id,
        )

        # 2. Ingest frontdesk.source_reported
        source_ev = IngestEventItem(
            event_type="frontdesk.source_reported",
            occurred_at=now,
            idempotency_key=f"fd_src_{contact_id}_{int(now.timestamp())}",
            contact_id=contact_id,
            tracking_code=req.tracking_code,
            location_id=req.location_id,
            source="frontdesk",
            properties={"reported_source": req.source_reported},
        )

        events_to_process = [source_ev]

        # 3. If trial or membership, add conversion event
        if req.event_type != "frontdesk.source_reported":
            action_ev = IngestEventItem(
                event_type=req.event_type,
                occurred_at=now,
                idempotency_key=f"fd_action_{contact_id}_{req.event_type}_{int(now.timestamp())}",
                contact_id=contact_id,
                tracking_code=req.tracking_code,
                location_id=req.location_id,
                source="frontdesk",
                value_minor=req.value_minor or 0,
            )
            events_to_process.append(action_ev)

        process_event_batch(session, biz_id, events_to_process)

    return {"status": "success", "contact_id": str(contact_id)}

"""Events ingestion API router."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from src.engine.db.session import tenant_session
from src.engine.ingest.service import IngestEventItem, IngestEventResponse, process_event_batch

router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("", response_model=list[IngestEventResponse])
def ingest_events_endpoint(
    events: list[IngestEventItem],
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[IngestEventResponse]:
    """Ingests a batch of up to 500 events."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        responses = process_event_batch(session, biz_id, events)
        return responses

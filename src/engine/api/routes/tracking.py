"""Tracking links generation, public redirection, and deep link builder."""

import random
import urllib.parse
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text

from src.engine.db.session import admin_session, tenant_session
from src.engine.ingest.service import IngestEventItem, process_event_batch

router = APIRouter(tags=["tracking"])

# Unambiguous 8-character alphabet (no 0/O, 1/I/l)
UNAMBIGUOUS_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz"


def generate_short_code(length: int = 8) -> str:
    return "".join(random.choices(UNAMBIGUOUS_ALPHABET, k=length))


class CreateTrackingLinkRequest(BaseModel):
    kind: str = "url"  # 'url', 'qr', 'whatsapp'
    destination: str | None = "https://example.com"
    campaign_id: UUID | None = None
    asset_id: UUID | None = None
    location_id: UUID | None = None


@router.post("/v1/tracking-links")
def create_tracking_link(
    req: CreateTrackingLinkRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, str]:
    """Generates an unambiguous 8-character tracking short code."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    code = generate_short_code()

    with tenant_session(biz_id) as session:
        session.execute(
            text("""
                INSERT INTO tracking_links (
                    id, business_id, campaign_id, asset_id, location_id, code, kind, destination, created_at
                )
                VALUES (
                    :id, :biz_id, :camp_id, :ast_id, :loc_id, :code, :kind, :dest, now()
                )
            """),
            {
                "id": str(uuid4()),
                "biz_id": str(biz_id),
                "camp_id": str(req.campaign_id) if req.campaign_id else None,
                "ast_id": str(req.asset_id) if req.asset_id else None,
                "loc_id": str(req.location_id) if req.location_id else None,
                "code": code,
                "kind": req.kind,
                "dest": req.destination,
            },
        )

    return {"code": code, "short_url": f"/t/{code}"}


@router.get("/t/{code}")
def redirect_tracking_link(
    code: str,
    request: Request,
) -> Response:
    """
    Public tracking link redirect:
    1. Sets anonymous_id cookie if not present.
    2. Ingests an ad.click event with tracking_code.
    3. Redirects to target destination.
    """
    anon_id = request.cookies.get("anon_id") or f"anon_{uuid4().hex}"
    now = datetime.now(UTC)

    # Lookup code
    with admin_session() as session:
        row = session.execute(
            text("""
                SELECT business_id, destination, campaign_id, asset_id, location_id
                FROM tracking_links WHERE code = :code
            """),
            {"code": code},
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Tracking link not found.")

        biz_id = UUID(str(row[0]))
        destination = str(row[1]) if row[1] else "https://example.com"
        camp_id = UUID(str(row[2])) if row[2] else None
        ast_id = UUID(str(row[3])) if row[3] else None
        loc_id = UUID(str(row[4])) if row[4] else None

    # Ingest click under tenant session
    with tenant_session(biz_id) as t_session:
        click_event = IngestEventItem(
            event_type="ad.click",
            occurred_at=now,
            idempotency_key=f"click_{code}_{anon_id}_{int(now.timestamp())}",
            anonymous_id=anon_id,
            tracking_code=code,
            campaign_id=camp_id,
            asset_id=ast_id,
            location_id=loc_id,
            source="tracking_link",
        )
        process_event_batch(t_session, biz_id, [click_event])

    response = RedirectResponse(url=destination, status_code=302)
    response.set_cookie("anon_id", anon_id, max_age=86400 * 30, httponly=True)
    return response


@router.get("/v1/tracking-links/{code}/whatsapp")
def build_whatsapp_deeplink(
    code: str,
    phone_number: str = "919876543210",
) -> dict[str, str]:
    """Generates a WhatsApp click-to-chat deep link with prefilled tracking code."""
    prefilled_text = f"Hi! I'm interested in booking a trial session. Ref: [{code}]"
    encoded_text = urllib.parse.quote(prefilled_text)
    deeplink = f"https://wa.me/{phone_number}?text={encoded_text}"
    return {"code": code, "deeplink": deeplink}

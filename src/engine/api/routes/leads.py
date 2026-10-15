"""Leads capture and WhatsApp webhook endpoints."""

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.engine.config import get_settings
from src.engine.db.session import tenant_session
from src.engine.identity.consent import is_stop_keyword
from src.engine.identity.crypto import (
    compute_identifier_hash,
    derive_tenant_hmac_key,
    normalize_phone_number,
)
from src.engine.identity.resolution import link_identity, upsert_contact_by_identifier
from src.engine.ingest.service import IngestEventItem, process_event_batch

settings = get_settings()
router = APIRouter(tags=["leads"])


class LeadCaptureRequest(BaseModel):
    full_name: str
    phone: str
    email: str | None = None
    consent_granted: bool
    consent_evidence: dict[str, Any] = Field(default_factory=dict)
    tracking_code: str | None = None
    anonymous_id: str | None = None
    location_id: UUID | None = None


@router.post("/v1/leads")
def capture_lead_endpoint(
    req: LeadCaptureRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Captures a new lead via web form with explicit affirmative consent."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    if not req.consent_granted:
        raise HTTPException(
            status_code=422, detail="Affirmative consent checkbox is required by DPDP regulations."
        )

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
            email=req.email,
            location_id=req.location_id,
        )

        # 2. Store consent ledger row
        session.execute(
            text("""
                INSERT INTO consents (
                    id, business_id, contact_id, channel, purpose, status, source, evidence, occurred_at
                )
                VALUES (
                    :id, :biz_id, :c_id, 'whatsapp', 'marketing', 'granted', 'lead_form', :ev, :occ
                )
            """),
            {
                "id": str(uuid4()),
                "biz_id": str(biz_id),
                "c_id": str(contact_id),
                "ev": json.dumps(req.consent_evidence),
                "occ": now,
            },
        )

        # 3. Link anonymous ID if present
        if req.anonymous_id:
            link_identity(
                session=session,
                business_id=biz_id,
                anonymous_id=req.anonymous_id,
                contact_id=contact_id,
                method="form_submit",
                confidence=1.0,
            )

        # 4. Ingest form.submitted event
        event_item = IngestEventItem(
            event_type="form.submitted",
            occurred_at=now,
            idempotency_key=f"lead_form_{contact_id}_{now.timestamp()}",
            contact_id=contact_id,
            anonymous_id=req.anonymous_id,
            tracking_code=req.tracking_code,
            location_id=req.location_id,
            source="lead_form",
            properties={"name": req.full_name},
        )
        process_event_batch(session, biz_id, [event_item])

        return {"status": "success", "contact_id": str(contact_id)}


@router.get("/v1/webhooks/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
) -> Response:
    """WhatsApp verification challenge handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification token mismatch.")


@router.post("/v1/webhooks/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, str]:
    """
    Receives incoming WhatsApp Cloud API webhooks.
    Validates X-Hub-Signature-256 against WHATSAPP_APP_SECRET.
    Processes STOP keywords for automatic opt-out.
    """
    body_bytes = await request.body()

    # Verify signature
    if not settings.dry_run:
        if not x_hub_signature_256:
            raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256.")

        expected_sig = (
            "sha256="
            + hmac.new(
                settings.whatsapp_app_secret.encode("utf-8"), body_bytes, hashlib.sha256
            ).hexdigest()
        )

        if not hmac.compare_digest(expected_sig, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return {"status": "ignored"}

    # Extract business_id
    biz_id_str = x_business_id or data.get("business_id")
    if not biz_id_str:
        return {"status": "ok"}
    biz_id = UUID(biz_id_str)

    now = datetime.now(UTC)
    entries = data.get("entry", [])

    with tenant_session(biz_id) as session:
        for entry in entries:
            for change in entry.get("changes", []):
                val = change.get("value", {})
                messages = val.get("messages", [])
                for msg in messages:
                    msg_id = msg.get("id", uuid4().hex)
                    from_phone = msg.get("from", "")
                    msg_text = msg.get("text", {}).get("body", "")

                    if not from_phone:
                        continue

                    # Upsert contact
                    contact_id = upsert_contact_by_identifier(
                        session=session,
                        business_id=biz_id,
                        identifier_type="phone",
                        raw_value=from_phone,
                        phone=from_phone,
                    )

                    # Check for STOP keyword
                    if is_stop_keyword(msg_text):
                        # 1. Record withdrawn consent
                        session.execute(
                            text("""
                                INSERT INTO consents (
                                    id, business_id, contact_id, channel, purpose, status, source, evidence, occurred_at
                                )
                                VALUES (
                                    :id, :biz_id, :c_id, 'whatsapp', 'marketing', 'withdrawn', 'stop_keyword', :ev, :occ
                                )
                            """),
                            {
                                "id": str(uuid4()),
                                "biz_id": str(biz_id),
                                "c_id": str(contact_id),
                                "ev": json.dumps({"text": msg_text}),
                                "occ": now,
                            },
                        )

                        # 2. Add to suppressions
                        tenant_key = derive_tenant_hmac_key(settings.hmac_key_bytes, biz_id)
                        val_hash = compute_identifier_hash(
                            normalize_phone_number(from_phone), tenant_key
                        )
                        session.execute(
                            text("""
                                INSERT INTO suppressions (business_id, channel, value_hash, reason, created_at)
                                VALUES (:biz_id, 'whatsapp', :v_hash, 'opt_out', now())
                                ON CONFLICT (business_id, channel, value_hash) DO NOTHING
                            """),
                            {"biz_id": str(biz_id), "v_hash": val_hash},
                        )

                        # 3. Ingest consent.withdrawn event
                        event_item = IngestEventItem(
                            event_type="consent.withdrawn",
                            occurred_at=now,
                            idempotency_key=f"optout_{msg_id}",
                            contact_id=contact_id,
                            source="whatsapp_webhook",
                        )
                        process_event_batch(session, biz_id, [event_item])

                    else:
                        # Standard inbound message: ingest message.inbound event
                        event_item = IngestEventItem(
                            event_type="message.inbound",
                            occurred_at=now,
                            idempotency_key=f"wa_in_{msg_id}",
                            contact_id=contact_id,
                            source="whatsapp_webhook",
                            properties={"text": msg_text},
                        )
                        process_event_batch(session, biz_id, [event_item])

    return {"status": "processed"}

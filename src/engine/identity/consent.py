"""Consent management, ledger tracking, and STOP-keyword detection."""

import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

STOP_KEYWORDS: set[str] = {
    # English
    "stop",
    "unsubscribe",
    "cancel",
    "no more",
    "quit",
    "end",
    "halt",
    # Hindi / Hinglish
    "ruk",
    "ruko",
    "band karo",
    "mat bhejo",
    "roko",
    # Kannada
    "nillisi",
    "beda",
    "saku",
    "nillisu",
}


def is_stop_keyword(message_text: str) -> bool:
    """Checks whether an inbound message matches any universal stop keywords."""
    cleaned = re.sub(r"[^\w\s]", "", message_text.strip().lower())
    words = cleaned.split()
    if cleaned in STOP_KEYWORDS:
        return True
    return any(w in STOP_KEYWORDS for w in words)


def assert_consent(session: Session, contact_id: UUID, channel: str) -> None:
    """
    Asserts marketing consent for a contact on a given channel.
    Raises RuntimeError if consent is missing or not granted.
    """
    row = session.execute(
        text("""
            SELECT status FROM v_consent_current
            WHERE contact_id = :contact_id
              AND channel = :channel
              AND purpose = 'marketing'
        """),
        {"contact_id": str(contact_id), "channel": channel},
    ).fetchone()

    if not row or row[0] != "granted":
        raise RuntimeError(f"No valid marketing consent for contact {contact_id} on {channel}")

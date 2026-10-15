"""Identity resolution, contact deduplication, merging, and erasure."""

from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.config import get_settings
from src.engine.identity.crypto import (
    compute_identifier_hash,
    derive_tenant_hmac_key,
    encrypt_pii,
    normalize_phone_number,
)

settings = get_settings()


def upsert_contact_by_identifier(
    session: Session,
    business_id: UUID,
    identifier_type: str,
    raw_value: str,
    full_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    segment_key: str | None = None,
    location_id: UUID | None = None,
) -> UUID:
    """
    Upserts a contact based on hashed identifier. If an existing contact
    is found, returns it; otherwise creates a new contact and encrypts PII.
    """
    norm_value = raw_value.strip().lower()
    if identifier_type == "phone":
        norm_value = normalize_phone_number(norm_value)

    tenant_key = derive_tenant_hmac_key(settings.hmac_key_bytes, business_id)
    val_hash = compute_identifier_hash(norm_value, tenant_key)

    # Check for existing identifier
    row = session.execute(
        text("""
            SELECT contact_id FROM contact_identifiers
            WHERE business_id = :biz_id AND type = :id_type AND value_hash = :v_hash
        """),
        {"biz_id": str(business_id), "id_type": identifier_type, "v_hash": val_hash},
    ).fetchone()

    if row:
        contact_id = UUID(str(row[0]))
        return contact_id

    # Create new contact
    new_contact_id = uuid4()
    session.execute(
        text("""
            INSERT INTO contacts (id, business_id, location_id, segment_key, status)
            VALUES (:id, :biz_id, :loc_id, :seg_key, 'lead')
        """),
        {
            "id": str(new_contact_id),
            "biz_id": str(business_id),
            "loc_id": str(location_id) if location_id else None,
            "seg_key": segment_key,
        },
    )

    # Insert hashed identifier
    session.execute(
        text("""
            INSERT INTO contact_identifiers (id, business_id, contact_id, type, value_hash, verified)
            VALUES (:id, :biz_id, :contact_id, :type, :val_hash, true)
        """),
        {
            "id": str(uuid4()),
            "biz_id": str(business_id),
            "contact_id": str(new_contact_id),
            "type": identifier_type,
            "val_hash": val_hash,
        },
    )

    # Encrypt PII in contact_pii
    pii_key = settings.pii_key_bytes
    name_enc = encrypt_pii(full_name, pii_key) if full_name else None
    phone_enc = encrypt_pii(phone, pii_key) if phone else None
    email_enc = encrypt_pii(email, pii_key) if email else None

    session.execute(
        text("""
            INSERT INTO contact_pii (contact_id, business_id, full_name_enc, phone_enc, email_enc)
            VALUES (:contact_id, :biz_id, :name_enc, :phone_enc, :email_enc)
        """),
        {
            "contact_id": str(new_contact_id),
            "biz_id": str(business_id),
            "name_enc": name_enc,
            "phone_enc": phone_enc,
            "email_enc": email_enc,
        },
    )

    return new_contact_id


def link_identity(
    session: Session,
    business_id: UUID,
    anonymous_id: str,
    contact_id: UUID,
    method: str,
    confidence: float = 1.0,
) -> None:
    """Links an anonymous ID to a known contact with specified confidence."""
    session.execute(
        text("""
            INSERT INTO identity_links (id, business_id, anonymous_id, contact_id, method, confidence)
            VALUES (:id, :biz_id, :anon_id, :contact_id, :method, :confidence)
            ON CONFLICT (business_id, anonymous_id, contact_id) DO UPDATE
            SET confidence = EXCLUDED.confidence, linked_at = now()
        """),
        {
            "id": str(uuid4()),
            "biz_id": str(business_id),
            "anon_id": anonymous_id,
            "contact_id": str(contact_id),
            "method": method,
            "confidence": confidence,
        },
    )


def merge_contacts(
    session: Session,
    business_id: UUID,
    primary_contact_id: UUID,
    secondary_contact_id: UUID,
) -> None:
    """
    Merges secondary contact into primary contact:
    Re-points children (identifiers, identity_links, conversations, events),
    deletes secondary contact, and records a system 'contact.merged' event.
    """
    if primary_contact_id == secondary_contact_id:
        return

    # Re-point identifiers
    session.execute(
        text("UPDATE contact_identifiers SET contact_id = :p_id WHERE contact_id = :s_id"),
        {"p_id": str(primary_contact_id), "s_id": str(secondary_contact_id)},
    )

    # Re-point identity_links
    session.execute(
        text("UPDATE identity_links SET contact_id = :p_id WHERE contact_id = :s_id"),
        {"p_id": str(primary_contact_id), "s_id": str(secondary_contact_id)},
    )

    # Re-point conversations
    session.execute(
        text("UPDATE conversations SET contact_id = :p_id WHERE contact_id = :s_id"),
        {"p_id": str(primary_contact_id), "s_id": str(secondary_contact_id)},
    )

    # Re-point consents
    session.execute(
        text("UPDATE consents SET contact_id = :p_id WHERE contact_id = :s_id"),
        {"p_id": str(primary_contact_id), "s_id": str(secondary_contact_id)},
    )

    # Delete secondary contact (cascades to remaining secondary pii)
    session.execute(
        text("DELETE FROM contacts WHERE id = :s_id"), {"s_id": str(secondary_contact_id)}
    )

    # Insert audit log
    session.execute(
        text("""
            INSERT INTO audit_log (business_id, actor_kind, actor_id, action, entity_type, entity_id, diff)
            VALUES (:biz_id, 'system', 'identity_resolver', 'merge_contacts', 'contacts', :p_id, :diff)
        """),
        {
            "biz_id": str(business_id),
            "p_id": str(primary_contact_id),
            "diff": f'{{"merged_from": "{secondary_contact_id}"}}',
        },
    )


def erase_contact_pii(session: Session, business_id: UUID, contact_id: UUID) -> None:
    """
    DPDP-compliant hard erasure of PII for a contact.
    Deletes contact_pii, contact_identifiers, identity_links, and clears message bodies.
    Sets contacts.erased_at = now().
    """
    # 1. Delete contact_pii
    session.execute(
        text("DELETE FROM contact_pii WHERE contact_id = :c_id"), {"c_id": str(contact_id)}
    )

    # 2. Delete identifiers
    session.execute(
        text("DELETE FROM contact_identifiers WHERE contact_id = :c_id"), {"c_id": str(contact_id)}
    )

    # 3. Delete identity links
    session.execute(
        text("DELETE FROM identity_links WHERE contact_id = :c_id"), {"c_id": str(contact_id)}
    )

    # 4. Clear message bodies in conversations
    session.execute(
        text("""
            UPDATE messages SET body_enc = NULL
            WHERE conversation_id IN (
                SELECT id FROM conversations WHERE contact_id = :c_id
            )
        """),
        {"c_id": str(contact_id)},
    )

    # 5. Set contacts.erased_at
    session.execute(
        text("UPDATE contacts SET erased_at = now() WHERE id = :c_id"), {"c_id": str(contact_id)}
    )

    # 6. Audit log
    session.execute(
        text("""
            INSERT INTO audit_log (business_id, actor_kind, actor_id, action, entity_type, entity_id, diff)
            VALUES (:biz_id, 'system', 'erasure_service', 'erase_pii', 'contacts', :c_id, '{"erased": true}')
        """),
        {"biz_id": str(business_id), "c_id": str(contact_id)},
    )

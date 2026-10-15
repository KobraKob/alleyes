"""Identity, PII encryption, consent, and resolution module."""

from src.engine.identity.consent import STOP_KEYWORDS, assert_consent, is_stop_keyword
from src.engine.identity.crypto import (
    compute_identifier_hash,
    decrypt_pii,
    derive_tenant_hmac_key,
    encrypt_pii,
    normalize_phone_number,
)
from src.engine.identity.resolution import (
    erase_contact_pii,
    link_identity,
    merge_contacts,
    upsert_contact_by_identifier,
)

__all__ = [
    "normalize_phone_number",
    "derive_tenant_hmac_key",
    "compute_identifier_hash",
    "encrypt_pii",
    "decrypt_pii",
    "is_stop_keyword",
    "assert_consent",
    "STOP_KEYWORDS",
    "upsert_contact_by_identifier",
    "link_identity",
    "merge_contacts",
    "erase_contact_pii",
]

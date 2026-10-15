"""Unit tests for PII encryption, normalization, and tenant HMAC isolation."""

import os
from uuid import uuid4

from src.engine.identity.crypto import (
    compute_identifier_hash,
    decrypt_pii,
    derive_tenant_hmac_key,
    encrypt_pii,
    normalize_phone_number,
)


def test_phone_normalization_e164() -> None:
    assert normalize_phone_number("9876543210") == "+919876543210"
    assert normalize_phone_number("09876543210") == "+919876543210"
    assert normalize_phone_number("+91 98765-43210") == "+919876543210"
    assert normalize_phone_number("+1 (555) 123-4567") == "+15551234567"


def test_aes_gcm_pii_roundtrip() -> None:
    key = os.urandom(32)
    plaintext = "Alex Mercer, alex@ironfit.com, +919876543210"
    encrypted = encrypt_pii(plaintext, key)
    assert encrypted != plaintext.encode()
    assert len(encrypted) > len(plaintext)

    decrypted = decrypt_pii(encrypted, key)
    assert decrypted == plaintext


def test_tenant_hmac_isolation() -> None:
    master_key = os.urandom(32)
    biz_a = uuid4()
    biz_b = uuid4()

    key_a = derive_tenant_hmac_key(master_key, biz_a)
    key_b = derive_tenant_hmac_key(master_key, biz_b)

    assert key_a != key_b

    phone = "+919876543210"
    hash_a = compute_identifier_hash(phone, key_a)
    hash_b = compute_identifier_hash(phone, key_b)

    # Identical phone must yield different hashes across tenants
    assert hash_a != hash_b

"""Cryptographic services: AES-256-GCM for PII and HKDF-HMAC for tenant-keyed hashing."""

import os
import re
from uuid import UUID

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def normalize_phone_number(phone: str, default_region: str = "91") -> str:
    """
    Normalizes a phone number to standard E.164 format.
    Defaults to Indian country code '+91' if missing.
    """
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if len(cleaned) == 10:
        return f"+{default_region}{cleaned}"
    if cleaned.startswith(default_region) and len(cleaned) == 12:
        return f"+{cleaned}"
    return f"+{cleaned}"


def derive_tenant_hmac_key(master_key: bytes, business_id: UUID) -> bytes:
    """
    Derives a tenant-unique HMAC key from the master secret using HKDF-SHA256
    with business_id bytes as the salt.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=business_id.bytes,
        info=b"tenant-hmac-v1",
    )
    return hkdf.derive(master_key)


def compute_identifier_hash(value: str, tenant_hmac_key: bytes) -> bytes:
    """
    Computes an HMAC-SHA256 hash of an identifier using the tenant's derived key.
    """
    h = hmac.HMAC(tenant_hmac_key, hashes.SHA256())
    h.update(value.strip().lower().encode("utf-8"))
    return h.finalize()


def encrypt_pii(plaintext: str, key: bytes) -> bytes:
    """
    Encrypts plaintext using AES-256-GCM.
    Returns: nonce (12 bytes) || ciphertext + tag (16 bytes).
    """
    if not plaintext:
        return b""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_pii(payload: bytes | None, key: bytes) -> str:
    """
    Decrypts AES-256-GCM payload: nonce (12 bytes) || ciphertext + tag.
    """
    if not payload or len(payload) <= 12:
        return ""
    aesgcm = AESGCM(key)
    nonce = payload[:12]
    ciphertext = payload[12:]
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_bytes.decode("utf-8")

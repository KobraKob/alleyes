"""Authentication and authorization utilities: API key hash checking and JWT tokens."""

from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.config import get_settings

settings = get_settings()
ph = PasswordHasher()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security_bearer = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    """Hashes an API key using Argon2id."""
    return ph.hash(raw_key)


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verifies raw API key against Argon2id hash."""
    try:
        return ph.verify(hashed_key, raw_key)
    except VerifyMismatchError:
        return False


def get_business_id_from_api_key(
    session: Session,
    raw_key: str | None = Security(api_key_header),
) -> UUID:
    """
    Validates API key from X-API-Key header against database.
    Matches prefix first, then verifies argon2 hash.
    """
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing required X-API-Key header."
        )

    prefix = raw_key[:8]
    candidates = session.execute(
        text("""
            SELECT business_id, key_hash FROM api_keys
            WHERE key_prefix = :prefix AND revoked_at IS NULL
        """),
        {"prefix": prefix},
    ).fetchall()

    for biz_id, k_hash in candidates:
        if verify_api_key(raw_key, k_hash):
            return UUID(str(biz_id))

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key."
    )

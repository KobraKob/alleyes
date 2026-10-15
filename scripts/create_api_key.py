"""Provision a tenant API key. The raw key is printed once and is never stored."""

import argparse
import secrets
from uuid import UUID

from src.engine.api.auth import hash_api_key
from src.engine.db.session import admin_session
from sqlalchemy import text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--business-id", required=True, type=UUID)
    parser.add_argument("--name", default="production")
    args = parser.parse_args()

    raw_key = "al_" + secrets.token_urlsafe(36)
    with admin_session() as session:
        exists = session.execute(
            text("SELECT 1 FROM businesses WHERE id = :business_id"),
            {"business_id": str(args.business_id)},
        ).first()
        if not exists:
            parser.error("Business ID does not exist.")
        session.execute(
            text("""
                INSERT INTO api_keys (business_id, key_prefix, key_hash, name)
                VALUES (:business_id, :prefix, :key_hash, :name)
            """),
            {
                "business_id": str(args.business_id),
                "prefix": raw_key[:8],
                "key_hash": hash_api_key(raw_key),
                "name": args.name,
            },
        )
    print("API key created. Store it in your secret manager; it cannot be recovered.")
    print(raw_key)


if __name__ == "__main__":
    main()

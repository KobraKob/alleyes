"""0003_api_keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14 22:32:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    statements = [
        """
        CREATE TABLE api_keys (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            business_id uuid NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
            key_prefix text NOT NULL,
            key_hash text NOT NULL,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz
        )
        """,
        "CREATE INDEX api_keys_lookup_idx ON api_keys (key_prefix) WHERE revoked_at IS NULL",
        "ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE api_keys FORCE ROW LEVEL SECURITY",
        """CREATE POLICY tenant_isolation ON api_keys
           USING (business_id = current_setting('app.business_id', true)::uuid)""",
    ]
    conn = op.get_bind()
    for statement in statements:
        conn.exec_driver_sql(statement)

def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS api_keys CASCADE;"))

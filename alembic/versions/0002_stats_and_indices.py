"""0002_stats_and_indices

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14 22:31:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    statements = [
        "ALTER TABLE decisions ADD COLUMN stats_applied_reward numeric(12,4) NOT NULL DEFAULT 0",
        "ALTER TABLE decisions ADD COLUMN stats_counted boolean NOT NULL DEFAULT false",
        "CREATE INDEX decisions_pending_idx ON decisions (business_id, decided_at) WHERE stats_counted = false",
        "CREATE INDEX rewards_decision_idx ON rewards (decision_id, observed_at DESC)",
        "CREATE INDEX actions_status_idx ON actions (business_id, status, proposed_at)",
        "CREATE INDEX messages_conv_idx ON messages (conversation_id, sent_at)",
        "CREATE INDEX conversions_biz_idx ON conversions (business_id, occurred_at DESC)",
    ]
    conn = op.get_bind()
    for statement in statements:
        conn.exec_driver_sql(statement)

def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DROP INDEX IF EXISTS conversions_biz_idx;
        DROP INDEX IF EXISTS messages_conv_idx;
        DROP INDEX IF EXISTS actions_status_idx;
        DROP INDEX IF EXISTS rewards_decision_idx;
        DROP INDEX IF EXISTS decisions_pending_idx;
        ALTER TABLE decisions DROP COLUMN IF EXISTS stats_counted;
        ALTER TABLE decisions DROP COLUMN IF EXISTS stats_applied_reward;
    """))

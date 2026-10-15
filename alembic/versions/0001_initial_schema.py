"""0001_initial_schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-14 22:30:00.000000
"""
from typing import Sequence, Union
from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    schema_path = Path(__file__).parent.parent.parent / "marketing_engine_schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")
    
    with open(schema_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Execute verbatim SQL
    conn = op.get_bind()
    conn.exec_driver_sql(sql_content)

def downgrade() -> None:
    raise RuntimeError("Downgrading initial schema is not supported in production.")

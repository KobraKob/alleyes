"""Database roles management and SQL scripts."""

from sqlalchemy import text
from sqlalchemy.engine import Engine

ROLES_DDL = """
-- Create DB roles if they do not exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_secret' NOBYPASSRLS;
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'learning_svc') THEN
        CREATE ROLE learning_svc WITH LOGIN PASSWORD 'learning_secret' BYPASSRLS;
    END IF;
END $$;

-- Grant permissions to app_user (RLS enforced)
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Grant permissions to learning_svc (Cross-tenant analysis only)
GRANT USAGE ON SCHEMA public TO learning_svc;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO learning_svc;
GRANT INSERT, UPDATE ON priors TO learning_svc;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO learning_svc;
"""


def create_db_roles(engine: Engine) -> None:
    """Executes the DDL script to create and grant roles."""
    with engine.begin() as conn:
        conn.execute(text(ROLES_DDL))

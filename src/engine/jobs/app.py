"""Procrastinate Postgres-backed queue configuration."""

import procrastinate

from src.engine.config import get_settings

settings = get_settings()

# Initialize procrastinate app
# Uses app_role_url or database_url
app = procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=settings.database_url))

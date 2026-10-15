"""Database session management with enforced Row-Level Security (RLS) contexts."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.engine.config import get_settings

settings = get_settings()

# Engine for regular application operations (RLS enforced role)
app_engine = create_engine(settings.app_role_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

# Engine for migrator / admin operations
migrator_engine = create_engine(
    settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=10
)

# Engine for learning cross-tenant aggregation (BYPASSRLS role)
learning_engine = create_engine(
    settings.learning_role_url, pool_pre_ping=True, pool_size=5, max_overflow=10
)

AppSessionLocal = sessionmaker(bind=app_engine, autoflush=False, autocommit=False)
MigratorSessionLocal = sessionmaker(bind=migrator_engine, autoflush=False, autocommit=False)
LearningSessionLocal = sessionmaker(bind=learning_engine, autoflush=False, autocommit=False)


@contextmanager
def tenant_session(business_id: Any | None = None) -> Generator[Session, None, None]:
    """
    Context manager that opens an application transaction and sets
    `SET LOCAL app.business_id = '<uuid>'`.
    Refuses to execute if business_id is missing or None.
    """
    if business_id is None:
        raise ValueError("Tenant isolation violation: business_id is required for tenant_session.")

    biz_uuid_str = str(UUID(str(business_id)))

    session: Session = AppSessionLocal()
    try:
        session.begin()
        # Set local variable for the transaction scope
        session.execute(text("SET LOCAL app.business_id = :biz_id"), {"biz_id": biz_uuid_str})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def learning_session() -> Generator[Session, None, None]:
    """
    Context manager for the learning service role (BYPASSRLS).
    Used strictly for cross-tenant priors aggregation jobs.
    """
    session: Session = LearningSessionLocal()
    try:
        session.begin()
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def admin_session() -> Generator[Session, None, None]:
    """
    Context manager for administrative tasks, seed data, and schema operations.
    """
    session: Session = MigratorSessionLocal()
    try:
        session.begin()
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

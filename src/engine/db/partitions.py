"""Event partition manager for PostgreSQL partitioned events table."""

from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine


def ensure_event_partitions(conn_or_engine: Engine | Connection) -> list[str]:
    """
    Ensures that partitions for events table exist for the current month,
    the next 3 months, and an events_default partition for fallbacks.
    Returns the names of partitions verified or created.
    """
    created_partitions: list[str] = []

    # 1. Create events_default if it doesn't exist
    create_default_sql = """
    CREATE TABLE IF NOT EXISTS events_default PARTITION OF events DEFAULT;
    """

    now = datetime.now(UTC)
    months_to_create = []
    for offset in range(4):  # Current month + 3 future months
        target_date = (now + relativedelta(months=offset)).replace(day=1)
        months_to_create.append(target_date)

    partition_statements = []
    for start_dt in months_to_create:
        end_dt = start_dt + relativedelta(months=1)
        part_name = f"events_{start_dt.strftime('%Y_%m')}"
        start_str = start_dt.strftime("%Y-%m-01")
        end_str = end_dt.strftime("%Y-%m-01")
        sql = f"""
        CREATE TABLE IF NOT EXISTS {part_name} PARTITION OF events
            FOR VALUES FROM ('{start_str}') TO ('{end_str}');
        """
        partition_statements.append((part_name, sql))

    def _execute(conn: Connection) -> None:
        conn.execute(text(create_default_sql))
        created_partitions.append("events_default")
        for part_name, sql in partition_statements:
            conn.execute(text(sql))
            created_partitions.append(part_name)

    if isinstance(conn_or_engine, Engine):
        with conn_or_engine.begin() as conn:
            _execute(conn)
    else:
        _execute(conn_or_engine)

    return created_partitions

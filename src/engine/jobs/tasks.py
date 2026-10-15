"""Procrastinate scheduled background tasks."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text

from src.engine.db.partitions import ensure_event_partitions
from src.engine.db.session import admin_session, tenant_session
from src.engine.jobs.app import app
from src.engine.learning.rewards import compute_decision_rewards
from src.engine.learning.updater import apply_nightly_discounting, update_arm_stats_batch


@app.task
def update_arm_stats_task(business_id_str: str) -> int:
    """Batch posterior updater task (runs every 15 min)."""
    biz_id = UUID(business_id_str)
    with tenant_session(biz_id) as session:
        return update_arm_stats_batch(session, biz_id)


@app.task
def compute_rewards_task(business_id_str: str) -> int:
    """Computes proxy and realized rewards for open decisions."""
    biz_id = UUID(business_id_str)
    with tenant_session(biz_id) as session:
        return compute_decision_rewards(session, biz_id)


@app.task
def apply_nightly_discounting_task(business_id_str: str) -> int:
    """Applies non-stationarity discount to bandit posteriors."""
    biz_id = UUID(business_id_str)
    with tenant_session(biz_id) as session:
        return apply_nightly_discounting(session, biz_id)


@app.task
def partition_maintenance_task() -> list[str]:
    """Ensures event partitions exist for rolling 4-month window."""
    with admin_session() as session:
        return ensure_event_partitions(session.connection())


@app.task
def data_retention_task(
    business_id_str: str, message_retention_months: int = 12, event_retention_months: int = 36
) -> int:
    """
    Enforces business data retention policies:
    Purges message bodies older than message_retention_months,
    and events older than event_retention_months.
    """
    biz_id = UUID(business_id_str)
    now = datetime.now(UTC)
    msg_cutoff = now - timedelta(days=message_retention_months * 30)
    event_cutoff = now - timedelta(days=event_retention_months * 30)

    with tenant_session(biz_id) as session:
        # 1. Nullify expired message bodies
        session.execute(
            text("""
                UPDATE messages
                SET body_enc = NULL
                WHERE business_id = :b AND sent_at < :cutoff AND body_enc IS NOT NULL
            """),
            {"b": str(biz_id), "cutoff": msg_cutoff},
        )

        # 2. Delete expired events
        res = session.execute(
            text("""
                DELETE FROM events
                WHERE business_id = :b AND occurred_at < :cutoff
            """),
            {"b": str(biz_id), "cutoff": event_cutoff},
        )
        rowcount = getattr(res, "rowcount", 0)
        return int(rowcount if rowcount is not None else 0)


@app.task
def evaluate_active_90d_members(business_id_str: str) -> int:
    """
    Daily job identifying members reaching day 90:
    Members with visit.checkin in the 30 days before day 90 and no membership.cancelled.
    Inserts 'active_90d' conversion and contact_stage_history.
    """
    biz_id = UUID(business_id_str)
    now = datetime.now(UTC)

    with tenant_session(biz_id) as session:
        # Fetch active_90d stage id
        stage_row = session.execute(
            text("SELECT id FROM funnel_stages WHERE business_id = :b AND key = 'active_90d'"),
            {"b": str(biz_id)},
        ).fetchone()

        if not stage_row:
            return 0
        stage_id = UUID(str(stage_row[0]))

        # Find members who entered 'member' stage ~90 days ago (between 90 and 95 days ago)
        # and have a checkin within the last 30 days, without a cancellation
        query = text("""
            SELECT m.contact_id
            FROM contact_stage_history m
            JOIN funnel_stages s ON s.id = m.stage_id AND s.key = 'member'
            WHERE m.business_id = :b
              AND m.entered_at <= :day_90
              AND NOT EXISTS (
                  SELECT 1 FROM events e
                  WHERE e.business_id = :b AND e.contact_id = m.contact_id
                    AND e.event_type = 'membership.cancelled'
              )
              AND EXISTS (
                  SELECT 1 FROM events e
                  WHERE e.business_id = :b AND e.contact_id = m.contact_id
                    AND e.event_type = 'visit.checkin'
                    AND e.occurred_at >= :day_60
              )
              AND NOT EXISTS (
                  SELECT 1 FROM contact_stage_history csh
                  WHERE csh.contact_id = m.contact_id AND csh.stage_id = :active_stage_id
              )
        """)

        qualified = session.execute(
            query,
            {
                "b": str(biz_id),
                "day_90": now - timedelta(days=90),
                "day_60": now - timedelta(days=30),
                "active_stage_id": str(stage_id),
            },
        ).fetchall()

        promoted = 0
        for r in qualified:
            c_id = UUID(str(r[0]))
            session.execute(
                text("""
                    INSERT INTO contact_stage_history (id, business_id, contact_id, stage_id, entered_at)
                    VALUES (gen_random_uuid(), :b, :c_id, :s_id, now())
                    ON CONFLICT (contact_id, stage_id) DO NOTHING
                """),
                {"b": str(biz_id), "c_id": str(c_id), "s_id": str(stage_id)},
            )
            session.execute(
                text("""
                    INSERT INTO conversions (id, business_id, contact_id, stage_id, occurred_at, value_minor, verified)
                    VALUES (gen_random_uuid(), :b, :c_id, :s_id, now(), 0, true)
                    ON CONFLICT (contact_id, stage_id) DO NOTHING
                """),
                {"b": str(biz_id), "c_id": str(c_id), "s_id": str(stage_id)},
            )
            promoted += 1

        return promoted


if __name__ == "__main__":
    # Standalone execution of worker
    print("Starting Procrastinate worker...")
    app.open()
    try:
        app.run_worker()
    finally:
        app.close()

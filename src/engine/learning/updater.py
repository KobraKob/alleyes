"""Bandit posterior stats updater running batch delta updates."""

import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.domain.bandits import apply_time_discount, update_beta_posterior


def update_arm_stats_batch(session: Session, business_id: UUID) -> int:
    """
    Updates arm_stats with delta rewards from new reward snapshots.
    Safe to re-run (idempotent deltas).
    Returns number of decisions processed.
    """
    # Find decisions that have rewards exceeding what was previously applied
    query = text("""
        SELECT d.id, d.chosen_arm_id, d.stats_applied_reward, d.stats_counted,
               d.context, r.value AS latest_value
        FROM decisions d
        JOIN LATERAL (
            SELECT value FROM rewards
            WHERE decision_id = d.id
            ORDER BY observed_at DESC LIMIT 1
        ) r ON true
        WHERE d.business_id = :biz_id
          AND (r.value > d.stats_applied_reward OR d.stats_counted = false)
    """)

    pending_decisions = session.execute(query, {"biz_id": str(business_id)}).fetchall()
    processed_count = 0

    for row in pending_decisions:
        dec_id = UUID(str(row[0]))
        arm_id = UUID(str(row[1]))
        applied_reward = float(row[2])
        stats_counted = bool(row[3])
        context = row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}")
        latest_value = float(row[5])

        segment_key = context.get("segment_key")
        segments = ["all"]
        if segment_key and segment_key != "all":
            segments.append(segment_key)

        delta = latest_value - applied_reward
        is_first_time = not stats_counted

        for seg in segments:
            # Fetch current arm stats for segment
            stat_row = session.execute(
                text("""
                    SELECT alpha, beta, n, reward_sum FROM arm_stats
                    WHERE business_id = :biz_id AND arm_id = :arm_id AND segment_key = :seg
                """),
                {"biz_id": str(business_id), "arm_id": str(arm_id), "seg": seg},
            ).fetchone()

            if stat_row:
                curr_alpha, curr_beta, curr_n, curr_sum = (
                    float(stat_row[0]),
                    float(stat_row[1]),
                    int(stat_row[2]),
                    float(stat_row[3]),
                )
            else:
                curr_alpha, curr_beta, curr_n, curr_sum = 1.0, 1.0, 0, 0.0

            new_alpha, new_beta = update_beta_posterior(
                current_alpha=curr_alpha,
                current_beta=curr_beta,
                current_applied_reward=applied_reward,
                new_cumulative_reward=latest_value,
                first_time=is_first_time,
            )

            new_n = curr_n + (1 if is_first_time else 0)
            new_sum = curr_sum + max(0.0, delta)

            session.execute(
                text("""
                    INSERT INTO arm_stats (
                        arm_id, business_id, segment_key, alpha, beta, n, reward_sum, updated_at
                    )
                    VALUES (
                        :arm_id, :biz_id, :seg, :alpha, :beta, :n, :reward_sum, now()
                    )
                    ON CONFLICT (arm_id, segment_key) DO UPDATE
                    SET alpha = EXCLUDED.alpha,
                        beta = EXCLUDED.beta,
                        n = EXCLUDED.n,
                        reward_sum = EXCLUDED.reward_sum,
                        updated_at = now()
                """),
                {
                    "arm_id": str(arm_id),
                    "biz_id": str(business_id),
                    "seg": seg,
                    "alpha": new_alpha,
                    "beta": new_beta,
                    "n": new_n,
                    "reward_sum": new_sum,
                },
            )

        # Mark decision with latest applied reward
        session.execute(
            text("""
                UPDATE decisions
                SET stats_applied_reward = :new_applied,
                    stats_counted = true
                WHERE id = :dec_id
            """),
            {"new_applied": latest_value, "dec_id": str(dec_id)},
        )
        processed_count += 1

    return processed_count


def apply_nightly_discounting(session: Session, business_id: UUID) -> int:
    """
    Applies nightly non-stationarity discounting to all arm_stats rows:
    multiplies (alpha - 1) and (beta - 1) by 0.995.
    """
    rows = session.execute(
        text("SELECT arm_id, segment_key, alpha, beta FROM arm_stats WHERE business_id = :biz_id"),
        {"biz_id": str(business_id)},
    ).fetchall()

    updated = 0
    for r in rows:
        arm_id, seg, alpha, beta = str(r[0]), str(r[1]), float(r[2]), float(r[3])
        new_a, new_b = apply_time_discount(alpha, beta, factor=0.995)
        session.execute(
            text("""
                UPDATE arm_stats
                SET alpha = :a, beta = :b, updated_at = now()
                WHERE business_id = :biz_id AND arm_id = :arm_id AND segment_key = :seg
            """),
            {"a": new_a, "b": new_b, "biz_id": str(business_id), "arm_id": arm_id, "seg": seg},
        )
        updated += 1

    return updated

"""Reward computation job for decisions."""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.domain.rewards import ConversionContribution, compute_normalized_reward


def compute_decision_rewards(
    session: Session,
    business_id: UUID,
    max_stage_weight: float = 25.0,
) -> int:
    """
    Computes cumulative snapshot rewards for decisions that have new conversions
    or are reaching their reward window maturity.
    Inserts 'proxy' or 'realized' rows into the rewards table.
    """
    now = datetime.now(UTC)

    # 1. Fetch decisions that do not have a finalized reward yet
    decisions_query = text("""
        SELECT d.id, d.decided_at, dp.reward_window_days
        FROM decisions d
        JOIN decision_points dp ON dp.id = d.decision_point_id
        LEFT JOIN (
            SELECT decision_id FROM rewards WHERE business_id = :biz_id AND is_final = true
        ) fin ON fin.decision_id = d.id
        WHERE d.business_id = :biz_id
          AND fin.decision_id IS NULL
    """)

    open_decisions = session.execute(decisions_query, {"biz_id": str(business_id)}).fetchall()

    rewards_inserted = 0

    for dec_row in open_decisions:
        dec_id = UUID(str(dec_row[0]))
        decided_at: datetime = dec_row[1]
        reward_window_days = int(dec_row[2])

        is_final = (now - decided_at) >= timedelta(days=reward_window_days)
        kind = "realized" if is_final else "proxy"

        # Find attributed conversions for this decision
        attr_query = text("""
            SELECT a.conversion_id, fs.key, fs.reward_weight, a.credit
            FROM attributions a
            JOIN conversions c ON c.id = a.conversion_id
            JOIN funnel_stages fs ON fs.id = c.stage_id
            WHERE a.business_id = :biz_id AND a.decision_id = :dec_id
        """)

        conv_rows = session.execute(
            attr_query, {"biz_id": str(business_id), "dec_id": str(dec_id)}
        ).fetchall()

        contributions = [
            ConversionContribution(
                conversion_id=UUID(str(r[0])),
                stage_key=str(r[1]),
                reward_weight=float(r[2]),
                credit=float(r[3]),
            )
            for r in conv_rows
        ]

        normalized_val, components = compute_normalized_reward(
            contributions=contributions,
            max_stage_weight=max_stage_weight,
        )

        # Check existing latest reward snapshot
        latest_row = session.execute(
            text("""
                SELECT value, is_final FROM rewards
                WHERE decision_id = :dec_id
                ORDER BY observed_at DESC LIMIT 1
            """),
            {"dec_id": str(dec_id)},
        ).fetchone()

        # If value has changed or transitioning to final, write snapshot
        should_insert = False
        if not latest_row:
            should_insert = (normalized_val > 0) or is_final
        else:
            prev_val = float(latest_row[0])
            prev_final = bool(latest_row[1])
            if abs(normalized_val - prev_val) > 1e-4 or (is_final and not prev_final):
                should_insert = True

        if should_insert:
            session.execute(
                text("""
                    INSERT INTO rewards (
                        id, business_id, decision_id, kind, value, components, is_final, observed_at
                    )
                    VALUES (
                        :id, :biz_id, :dec_id, :kind, :val, :components, :is_final, now()
                    )
                """),
                {
                    "id": str(uuid4()),
                    "biz_id": str(business_id),
                    "dec_id": str(dec_id),
                    "kind": kind,
                    "val": normalized_val,
                    "components": json.dumps(components),
                    "is_final": is_final,
                },
            )
            rewards_inserted += 1

    return rewards_inserted

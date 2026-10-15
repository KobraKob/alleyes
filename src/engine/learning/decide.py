"""The central decide() API: the single authorized entry point for autonomous choices."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.domain.bandits import ArmPosterior, select_arm
from src.engine.learning.priors import resolve_prior


@dataclass(frozen=True)
class DecisionRecord:
    id: UUID
    business_id: UUID
    decision_point_id: UUID
    chosen_arm_id: UUID
    candidate_arm_ids: list[UUID]
    propensity: float
    explored: bool
    policy_version: str
    context: dict[str, Any]
    decided_at: datetime
    contact_id: UUID | None = None
    campaign_id: UUID | None = None
    run_id: UUID | None = None


POLICY_VERSION_STRING = "thompson_beta_v1.0.0_eps0.05_m2000"


def decide(
    session: Session,
    *,
    business_id: UUID,
    decision_key: str,
    candidate_arm_ids: list[UUID],
    context: dict[str, Any],
    contact_id: UUID | None = None,
    campaign_id: UUID | None = None,
    run_id: UUID | None = None,
    rng: np.random.Generator | None = None,
    pack_config: dict[str, Any] | None = None,
) -> DecisionRecord:
    """
    Makes an autonomous decision among candidate arms using Thompson sampling
    with probability matching and an exploration floor.
    Logs the choice with its exact propensity in the decisions table.
    """
    if not candidate_arm_ids:
        raise ValueError("Cannot decide over an empty candidate_arm_ids list.")

    # 1. Fetch decision point
    dp_row = session.execute(
        text("""
            SELECT id FROM decision_points
            WHERE (business_id = :biz_id OR business_id IS NULL)
              AND key = :key
            ORDER BY business_id NULLS LAST
            LIMIT 1
        """),
        {"biz_id": str(business_id), "key": decision_key},
    ).fetchone()

    if not dp_row:
        raise ValueError(f"Unknown decision_point: {decision_key}")

    decision_point_id = UUID(str(dp_row[0]))

    # 2. Determine segment key from context
    proposed_segment = context.get("segment_key")
    chosen_segment = "all"

    if proposed_segment and proposed_segment != "all":
        # Check if arm_stats exists with n >= 30 for all candidate arms in this segment
        candidate_uuids = [str(a) for a in candidate_arm_ids]
        count_row = session.execute(
            text("""
                SELECT COUNT(*) FROM arm_stats
                WHERE business_id = :biz_id
                  AND segment_key = :seg
                  AND arm_id = ANY(:arm_ids)
                  AND n >= 30
            """),
            {"biz_id": str(business_id), "seg": proposed_segment, "arm_ids": candidate_uuids},
        ).fetchone()

        if count_row and count_row[0] == len(candidate_arm_ids):
            chosen_segment = proposed_segment

    # 3. Load posteriors or initialize with priors
    arms_data: list[ArmPosterior] = []
    for arm_id in candidate_arm_ids:
        stat_row = session.execute(
            text("""
                SELECT alpha, beta, n FROM arm_stats
                WHERE business_id = :biz_id
                  AND arm_id = :arm_id
                  AND segment_key = :seg
            """),
            {"biz_id": str(business_id), "arm_id": str(arm_id), "seg": chosen_segment},
        ).fetchone()

        if stat_row:
            arms_data.append(
                ArmPosterior(
                    arm_id=arm_id,
                    alpha=float(stat_row[0]),
                    beta=float(stat_row[1]),
                    n=int(stat_row[2]),
                    segment_key=chosen_segment,
                )
            )
        else:
            # Query arm signature for prior resolution
            sig_row = session.execute(
                text("SELECT signature FROM arms WHERE id = :arm_id"), {"arm_id": str(arm_id)}
            ).fetchone()
            signature = str(sig_row[0]) if sig_row else str(arm_id)

            prior = resolve_prior(
                session=session,
                business_id=business_id,
                decision_key=decision_key,
                arm_signature=signature,
                pack_config=pack_config,
            )

            # Insert initial arm_stats row
            session.execute(
                text("""
                    INSERT INTO arm_stats (arm_id, business_id, segment_key, alpha, beta, n)
                    VALUES (:arm_id, :biz_id, :seg, :alpha, :beta, 0)
                    ON CONFLICT (arm_id, segment_key) DO NOTHING
                """),
                {
                    "arm_id": str(arm_id),
                    "biz_id": str(business_id),
                    "seg": chosen_segment,
                    "alpha": prior.alpha,
                    "beta": prior.beta,
                },
            )

            arms_data.append(
                ArmPosterior(
                    arm_id=arm_id,
                    alpha=prior.alpha,
                    beta=prior.beta,
                    n=0,
                    segment_key=chosen_segment,
                )
            )

    # 4. Run Bandit Selection
    choice = select_arm(
        arms=arms_data,
        epsilon=0.05,
        num_draws=2000,
        rng=rng,
    )

    decision_id = uuid4()
    decided_at = datetime.now(UTC)

    # 5. Insert decision record
    session.execute(
        text("""
            INSERT INTO decisions (
                id, business_id, decision_point_id, chosen_arm_id, candidate_arm_ids,
                propensity, explored, policy_version, context, contact_id, campaign_id,
                run_id, decided_at, stats_applied_reward, stats_counted
            )
            VALUES (
                :id, :biz_id, :dp_id, :chosen_arm, :candidates,
                :propensity, :explored, :policy_ver, :context, :contact_id, :camp_id,
                :run_id, :decided_at, 0, false
            )
        """),
        {
            "id": str(decision_id),
            "biz_id": str(business_id),
            "dp_id": str(decision_point_id),
            "chosen_arm": str(choice.chosen_arm_id),
            "candidates": [str(a) for a in candidate_arm_ids],
            "propensity": choice.propensity,
            "explored": choice.explored,
            "policy_ver": POLICY_VERSION_STRING,
            "context": json.dumps(context),
            "contact_id": str(contact_id) if contact_id else None,
            "camp_id": str(campaign_id) if campaign_id else None,
            "run_id": str(run_id) if run_id else None,
            "decided_at": decided_at,
        },
    )

    return DecisionRecord(
        id=decision_id,
        business_id=business_id,
        decision_point_id=decision_point_id,
        chosen_arm_id=choice.chosen_arm_id,
        candidate_arm_ids=candidate_arm_ids,
        propensity=choice.propensity,
        explored=choice.explored,
        policy_version=POLICY_VERSION_STRING,
        context=context,
        decided_at=decided_at,
        contact_id=contact_id,
        campaign_id=campaign_id,
        run_id=run_id,
    )

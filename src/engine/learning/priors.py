"""Prior resolution and cross-tenant Bayesian prior aggregation."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PriorResult:
    alpha: float
    beta: float
    effective_n: float
    source: str  # 'business_all', 'cross_tenant_prior', 'pack_seed', 'uniform'


def resolve_prior(
    session: Session | None,
    business_id: UUID,
    decision_key: str,
    arm_signature: str,
    pack_config: dict[str, Any] | None = None,
) -> PriorResult:
    """
    Resolves Bayesian prior in strict order:
    1. Business 'all' stats: alpha0 = 1 + n0 * mean, beta0 = 1 + n0 * (1 - mean), n0 = 10
    2. Cross-tenant `priors` row (if contributing_tenants >= 5)
    3. Pack seed prior (from packs/gym/pack.yaml)
    4. Uniform Beta(1, 1) fallback
    """
    if session is not None:
        # 1. Check Business 'all' stats for this arm signature
        biz_row = session.execute(
            text("""
                SELECT s.alpha, s.beta, s.n FROM arm_stats s
                JOIN arms a ON a.id = s.arm_id
                JOIN decision_points dp ON dp.id = a.decision_point_id
                WHERE s.business_id = :biz_id
                  AND dp.key = :dec_key
                  AND a.signature = :sig
                  AND s.segment_key = 'all'
                  AND s.n >= 5
            """),
            {"biz_id": str(business_id), "dec_key": decision_key, "sig": arm_signature},
        ).fetchone()

        if biz_row:
            a, b, _n = float(biz_row[0]), float(biz_row[1]), int(biz_row[2])
            mean = a / (a + b) if (a + b) > 0 else 0.5
            n0 = 10.0
            return PriorResult(
                alpha=1.0 + n0 * mean,
                beta=1.0 + n0 * (1.0 - mean),
                effective_n=n0,
                source="business_all",
            )

        # 2. Check cross-tenant priors table (k-anonymity >= 5)
        prior_row = session.execute(
            text("""
                SELECT alpha, beta, effective_n FROM priors
                WHERE decision_key = :dec_key
                  AND arm_signature = :sig
                  AND contributing_tenants >= 5
                ORDER BY updated_at DESC
                LIMIT 1
            """),
            {"dec_key": decision_key, "sig": arm_signature},
        ).fetchone()

        if prior_row:
            eff_n = min(float(prior_row[2]), 20.0)  # Capped at 20 per spec
            return PriorResult(
                alpha=float(prior_row[0]),
                beta=float(prior_row[1]),
                effective_n=eff_n,
                source="cross_tenant_prior",
            )

    # 3. Check pack seed priors
    if pack_config and "seed_priors" in pack_config:
        seed_map = pack_config["seed_priors"]
        if arm_signature in seed_map:
            seed = seed_map[arm_signature]
            mean = float(seed.get("mean", 0.5))
            strength = float(seed.get("strength", 10.0))
            return PriorResult(
                alpha=1.0 + strength * mean,
                beta=1.0 + strength * (1.0 - mean),
                effective_n=strength,
                source="pack_seed",
            )

    # 4. Uniform fallback
    return PriorResult(alpha=1.0, beta=1.0, effective_n=2.0, source="uniform")

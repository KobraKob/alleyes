"""Off-Policy Evaluation (OPE): Inverse Propensity Scoring (IPS) & Self-Normalized IPS (SNIPS)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np


@dataclass(frozen=True)
class LoggedDecision:
    decision_id: UUID
    chosen_arm_id: UUID
    candidate_arm_ids: list[UUID]
    propensity: float  # Logging policy propensity p_0(a | x)
    observed_reward: float  # Final realized reward
    context: dict[str, Any]


@dataclass(frozen=True)
class OPEResult:
    value: float  # Estimated policy value (SNIPS)
    ips_value: float  # Standard IPS value
    ci_low: float  # Bootstrap 95% CI lower bound
    ci_high: float  # Bootstrap 95% CI upper bound
    effective_sample_size: float
    sample_count: int


def compute_ope_estimates(
    logged_data: Sequence[LoggedDecision],
    candidate_policy_fn: Callable[[dict[str, Any], list[UUID]], dict[UUID, float]],
    num_bootstrap: int = 1000,
    rng: np.random.Generator | None = None,
) -> OPEResult:
    """
    Computes IPS and SNIPS estimates of candidate policy value on logged bandit data.
    candidate_policy_fn(context, candidate_arms) -> {arm_id: candidate_propensity}
    Includes a 95% percentile bootstrap confidence interval and effective sample size.
    """
    if not logged_data:
        return OPEResult(
            value=0.0,
            ips_value=0.0,
            ci_low=0.0,
            ci_high=0.0,
            effective_sample_size=0.0,
            sample_count=0,
        )

    if rng is None:
        rng = np.random.default_rng()

    n = len(logged_data)
    importance_weights = np.zeros(n, dtype=np.float64)
    rewards = np.zeros(n, dtype=np.float64)

    for i, dec in enumerate(logged_data):
        target_probs = candidate_policy_fn(dec.context, dec.candidate_arm_ids)
        target_prop = float(target_probs.get(dec.chosen_arm_id, 0.0))
        logging_prop = max(float(dec.propensity), 1e-6)

        # Importance weight w_i = pi(a_i | x_i) / p_0(a_i | x_i)
        importance_weights[i] = target_prop / logging_prop
        rewards[i] = float(dec.observed_reward)

    # Standard IPS: (1 / n) * sum(w_i * r_i)
    weighted_rewards = importance_weights * rewards
    ips_val = float(np.mean(weighted_rewards))

    # Self-Normalized IPS (SNIPS): sum(w_i * r_i) / sum(w_i)
    weight_sum = float(np.sum(importance_weights))
    snips_val = float(np.sum(weighted_rewards) / weight_sum) if weight_sum > 0 else 0.0

    # Effective Sample Size: (sum(w_i))^2 / sum(w_i^2)
    sum_w_sq = float(np.sum(importance_weights**2))
    ess = float(weight_sum**2 / sum_w_sq) if sum_w_sq > 0 else 0.0

    # Bootstrap Confidence Interval (95%)
    boot_estimates = np.zeros(num_bootstrap, dtype=np.float64)
    for b in range(num_bootstrap):
        boot_idx = rng.choice(n, size=n, replace=True)
        boot_w = importance_weights[boot_idx]
        boot_r = rewards[boot_idx]
        b_sum_w = float(np.sum(boot_w))
        if b_sum_w > 0:
            boot_estimates[b] = float(np.sum(boot_w * boot_r) / b_sum_w)
        else:
            boot_estimates[b] = 0.0

    ci_low = float(np.percentile(boot_estimates, 2.5))
    ci_high = float(np.percentile(boot_estimates, 97.5))

    return OPEResult(
        value=round(snips_val, 4),
        ips_value=round(ips_val, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        effective_sample_size=round(ess, 2),
        sample_count=n,
    )

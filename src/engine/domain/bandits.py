"""Bandit algorithms, posterior sampling, Thompson Sampling, and probability matching."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np


@dataclass(frozen=True)
class ArmPosterior:
    arm_id: UUID
    alpha: float
    beta: float
    n: int = 0
    segment_key: str = "all"


@dataclass(frozen=True)
class BanditChoice:
    chosen_arm_id: UUID
    propensity: float
    explored: bool
    probabilities: dict[UUID, float]


def compute_arm_probabilities(
    arms: Sequence[ArmPosterior],
    epsilon: float = 0.05,
    num_draws: int = 2000,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Computes exact choice probabilities via Thompson posterior sampling
    mixed with uniform exploration:
    p'_i = (1 - epsilon) * p_i + epsilon / K
    Returns (mixed_probs, raw_thompson_probs).
    """
    if not arms:
        raise ValueError("Cannot decide over an empty set of candidate arms.")

    k = len(arms)
    if k == 1:
        # Single candidate has propensity 1.0
        return np.array([1.0], dtype=np.float64), np.array([1.0], dtype=np.float64)

    if rng is None:
        rng = np.random.default_rng()

    # Draw M samples for each candidate arm from Beta(alpha, beta)
    samples = np.zeros((num_draws, k), dtype=np.float64)
    for idx, arm in enumerate(arms):
        # Guard against zero or negative parameters
        a = max(float(arm.alpha), 1e-4)
        b = max(float(arm.beta), 1e-4)
        samples[:, idx] = rng.beta(a, b, size=num_draws)

    # p_i = fraction of draws in which arm i achieves the maximum sample
    max_indices = np.argmax(samples, axis=1)
    counts = np.bincount(max_indices, minlength=k)
    p_raw = counts.astype(np.float64) / float(num_draws)

    # Mix with uniform exploration
    p_mixed = (1.0 - epsilon) * p_raw + (epsilon / float(k))

    # Normalize to prevent floating point inaccuracies
    p_mixed = p_mixed / np.sum(p_mixed)
    return p_mixed, p_raw


def select_arm(
    arms: Sequence[ArmPosterior],
    epsilon: float = 0.05,
    num_draws: int = 2000,
    rng: np.random.Generator | None = None,
) -> BanditChoice:
    """
    Samples an arm from categorical distribution p_mixed.
    Returns BanditChoice with exact propensity and exploration flag.
    """
    if rng is None:
        rng = np.random.default_rng()

    p_mixed, p_raw = compute_arm_probabilities(
        arms=arms, epsilon=epsilon, num_draws=num_draws, rng=rng
    )

    k = len(arms)
    chosen_idx = int(rng.choice(k, p=p_mixed))
    greedy_idx = int(np.argmax(p_raw))

    chosen_arm = arms[chosen_idx]
    chosen_propensity = float(p_mixed[chosen_idx])
    explored = bool(chosen_idx != greedy_idx)

    prob_map = {arm.arm_id: float(p_mixed[i]) for i, arm in enumerate(arms)}

    return BanditChoice(
        chosen_arm_id=chosen_arm.arm_id,
        propensity=chosen_propensity,
        explored=explored,
        probabilities=prob_map,
    )


def update_beta_posterior(
    current_alpha: float,
    current_beta: float,
    current_applied_reward: float,
    new_cumulative_reward: float,
    first_time: bool,
) -> tuple[float, float]:
    """
    Updates Beta posterior with fractional reward.
    - delta = latest_cumulative_value - stats_applied_reward
    - If first time: alpha += r, beta += (1 - r)
    - Subsequent update raising from r0 to r1:
      alpha += (r1 - r0), beta -= (r1 - r0) (floor beta at 1e-4).
    """
    delta = new_cumulative_reward - current_applied_reward
    if delta < 0:
        # Negative deltas should not reduce learned stats
        return current_alpha, current_beta

    if first_time:
        new_alpha = current_alpha + new_cumulative_reward
        new_beta = current_beta + max(0.0, 1.0 - new_cumulative_reward)
    else:
        new_alpha = current_alpha + delta
        new_beta = max(1e-4, current_beta - delta)

    return float(new_alpha), float(new_beta)


def apply_time_discount(alpha: float, beta: float, factor: float = 0.995) -> tuple[float, float]:
    """
    Applies nightly non-stationarity time discounting:
    (alpha - 1) * factor + 1, (beta - 1) * factor + 1
    Floored at 1.0 (uniform prior baseline).
    """
    new_alpha = max(1.0, 1.0 + (alpha - 1.0) * factor)
    new_beta = max(1.0, 1.0 + (beta - 1.0) * factor)
    return float(new_alpha), float(new_beta)

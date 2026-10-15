"""Unit tests for bandit domain algorithms and Thompson sampling."""

from uuid import uuid4

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from src.engine.domain.bandits import (
    ArmPosterior,
    apply_time_discount,
    compute_arm_probabilities,
    select_arm,
    update_beta_posterior,
)


def test_single_arm_propensity() -> None:
    arm = ArmPosterior(arm_id=uuid4(), alpha=1.0, beta=1.0)
    choice = select_arm([arm])
    assert choice.propensity == 1.0
    assert not choice.explored


def test_propensities_sum_to_one() -> None:
    rng = np.random.default_rng(42)
    arms = [
        ArmPosterior(arm_id=uuid4(), alpha=5.0, beta=10.0),
        ArmPosterior(arm_id=uuid4(), alpha=20.0, beta=5.0),
        ArmPosterior(arm_id=uuid4(), alpha=1.0, beta=1.0),
    ]
    p_mixed, p_raw = compute_arm_probabilities(arms, epsilon=0.05, num_draws=2000, rng=rng)
    assert np.isclose(np.sum(p_mixed), 1.0, atol=1e-5)
    assert np.isclose(np.sum(p_raw), 1.0, atol=1e-5)


def test_determinism_with_same_rng() -> None:
    arms = [
        ArmPosterior(arm_id=uuid4(), alpha=10.0, beta=10.0),
        ArmPosterior(arm_id=uuid4(), alpha=5.0, beta=15.0),
    ]
    rng1 = np.random.default_rng(999)
    rng2 = np.random.default_rng(999)

    choice1 = select_arm(arms, rng=rng1)
    choice2 = select_arm(arms, rng=rng2)

    assert choice1.chosen_arm_id == choice2.chosen_arm_id
    assert np.isclose(choice1.propensity, choice2.propensity)


def test_dominant_arm_allocation() -> None:
    # Dominant arm has huge alpha, others have low alpha
    arms = [
        ArmPosterior(arm_id=uuid4(), alpha=100.0, beta=1.0),  # Dominant
        ArmPosterior(arm_id=uuid4(), alpha=1.0, beta=50.0),
        ArmPosterior(arm_id=uuid4(), alpha=1.0, beta=50.0),
    ]
    epsilon = 0.05
    k = 3
    expected_dominant_share = (1.0 - epsilon) + (epsilon / k)  # 0.95 + 0.0167 = ~0.9667

    p_mixed, _ = compute_arm_probabilities(arms, epsilon=epsilon, num_draws=5000)
    assert np.isclose(p_mixed[0], expected_dominant_share, atol=0.02)


def test_beta_posterior_delta_updates() -> None:
    # First application of 0.4 reward
    a1, b1 = update_beta_posterior(
        current_alpha=1.0,
        current_beta=1.0,
        current_applied_reward=0.0,
        new_cumulative_reward=0.4,
        first_time=True,
    )
    assert np.isclose(a1, 1.4)
    assert np.isclose(b1, 1.6)

    # Later snapshot raises reward from 0.4 to 0.7 (delta = 0.3)
    a2, b2 = update_beta_posterior(
        current_alpha=a1,
        current_beta=b1,
        current_applied_reward=0.4,
        new_cumulative_reward=0.7,
        first_time=False,
    )
    assert np.isclose(a2, 1.7)
    assert np.isclose(b2, 1.3)


def test_nightly_time_discounting() -> None:
    alpha, beta = 21.0, 41.0
    # (21 - 1) * 0.995 + 1 = 20 * 0.995 + 1 = 20.9
    # (41 - 1) * 0.995 + 1 = 40 * 0.995 + 1 = 40.8
    da, db = apply_time_discount(alpha, beta, factor=0.995)
    assert np.isclose(da, 20.9)
    assert np.isclose(db, 40.8)


@given(
    a1=st.floats(min_value=0.1, max_value=100.0),
    b1=st.floats(min_value=0.1, max_value=100.0),
    a2=st.floats(min_value=0.1, max_value=100.0),
    b2=st.floats(min_value=0.1, max_value=100.0),
)
def test_hypothesis_propensities_sum_to_one(a1: float, b1: float, a2: float, b2: float) -> None:
    arms = [
        ArmPosterior(arm_id=uuid4(), alpha=a1, beta=b1),
        ArmPosterior(arm_id=uuid4(), alpha=a2, beta=b2),
    ]
    p_mixed, _ = compute_arm_probabilities(arms, epsilon=0.05, num_draws=1000)
    assert np.isclose(np.sum(p_mixed), 1.0, atol=1e-4)

"""Unit tests for Off-Policy Evaluation (OPE)."""

from uuid import uuid4

import numpy as np
import pytest

from src.engine.learning.ope import LoggedDecision, compute_ope_estimates


def test_ope_with_known_ground_truth() -> None:
    # Generate synthetic logged data from uniform logging policy (propensity = 0.5)
    rng = np.random.default_rng(42)
    arm_a = uuid4()
    arm_b = uuid4()
    candidate_arms = [arm_a, arm_b]

    # Arm A true mean: 0.8; Arm B true mean: 0.2
    logged_data = []
    for _ in range(2000):
        chosen = arm_a if rng.random() < 0.5 else arm_b
        true_mean = 0.8 if chosen == arm_a else 0.2
        reward = 1.0 if rng.random() < true_mean else 0.0
        logged_data.append(
            LoggedDecision(
                decision_id=uuid4(),
                chosen_arm_id=chosen,
                candidate_arm_ids=candidate_arms,
                propensity=0.5,
                observed_reward=reward,
                context={},
            )
        )

    # Candidate Policy 1: Always choose Arm A (100% Arm A) -> True value is 0.8
    def policy_always_a(ctx, arms):
        return {arm_a: 1.0, arm_b: 0.0}

    res_a = compute_ope_estimates(logged_data, policy_always_a, num_bootstrap=500, rng=rng)

    assert pytest.approx(res_a.value, abs=0.05) == 0.8
    assert res_a.ci_low <= 0.8 <= res_a.ci_high

    # Candidate Policy 2: Always choose Arm B (100% Arm B) -> True value is 0.2
    def policy_always_b(ctx, arms):
        return {arm_a: 0.0, arm_b: 1.0}

    res_b = compute_ope_estimates(logged_data, policy_always_b, num_bootstrap=500, rng=rng)

    assert pytest.approx(res_b.value, abs=0.05) == 0.2
    assert res_b.ci_low <= 0.2 <= res_b.ci_high

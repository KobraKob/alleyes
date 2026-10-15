"""Unit tests for normalized reward calculations."""

from uuid import uuid4

import pytest

from src.engine.domain.rewards import (
    ConversionContribution,
    compute_normalized_reward,
)


def test_normalized_reward_clipping() -> None:
    # Large conversions exceeding max_stage_weight
    contributions = [
        ConversionContribution(
            conversion_id=uuid4(), stage_key="member", reward_weight=50.0, credit=1.0
        )
    ]
    reward, components = compute_normalized_reward(contributions, max_stage_weight=25.0)
    assert reward == 1.0
    assert components["member"] == 50.0


def test_calibrated_reward_multipliers() -> None:
    contributions = [
        ConversionContribution(
            conversion_id=uuid4(), stage_key="trial_attended", reward_weight=3.0, credit=1.0
        )
    ]
    # Calibrated: P(member | trial_attended) = 0.5 -> 3.0 * 0.5 = 1.5
    calib = {"trial_attended": 0.5}
    reward, components = compute_normalized_reward(
        contributions, max_stage_weight=25.0, calibration_multipliers=calib
    )
    assert pytest.approx(reward, abs=1e-3) == (1.5 / 25.0)
    assert pytest.approx(components["trial_attended"], abs=1e-3) == 1.5

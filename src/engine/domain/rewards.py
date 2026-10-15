"""Reward calculation logic."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ConversionContribution:
    conversion_id: UUID
    stage_key: str
    reward_weight: float
    credit: float


def compute_normalized_reward(
    contributions: Sequence[ConversionContribution],
    max_stage_weight: float = 25.0,
    calibration_multipliers: dict[str, float] | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Computes normalized reward:
    reward = clip( sum(stage.reward_weight * attribution.credit) / max_stage_weight, 0, 1 )
    Optionally applies calibrated conversion probabilities:
    weight = raw_weight * P(final success | stage).
    Returns (normalized_reward, component_breakdown).
    """
    if max_stage_weight <= 0:
        raise ValueError("max_stage_weight must be strictly positive.")

    raw_sum = 0.0
    components: dict[str, float] = {}

    for c in contributions:
        weight = c.reward_weight
        if calibration_multipliers and c.stage_key in calibration_multipliers:
            weight = weight * calibration_multipliers[c.stage_key]

        credited_val = weight * c.credit
        raw_sum += credited_val
        components[c.stage_key] = components.get(c.stage_key, 0.0) + credited_val

    normalized = max(0.0, min(1.0, raw_sum / max_stage_weight))
    return float(round(normalized, 4)), components

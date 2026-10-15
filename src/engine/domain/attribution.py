"""Multi-touch attribution models, candidate touch filtering, and credit assignment."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


@dataclass(frozen=True)
class TouchEvent:
    event_id: UUID
    event_type: str
    occurred_at: datetime
    campaign_id: UUID | None = None
    asset_id: UUID | None = None
    decision_id: UUID | None = None
    tracking_code: str | None = None
    match_method: str = "identity_link"
    confidence: float = 1.0


@dataclass(frozen=True)
class AttributionCredit:
    touch_event_id: UUID
    model: str
    credit: float
    match_method: str
    confidence: float
    campaign_id: UUID | None = None
    asset_id: UUID | None = None
    decision_id: UUID | None = None


TOUCH_TYPES = {"ad.click", "form.submitted", "message.inbound", "ad.impression"}


def filter_touches_within_lookback(
    touches: Sequence[TouchEvent],
    conversion_time: datetime,
    click_lookback_days: int = 30,
    impression_lookback_days: int = 7,
) -> list[TouchEvent]:
    """
    Filters touches to those preceding conversion within their respective lookback windows:
    - 30 days for click, form, inbound message
    - 7 days for impressions
    """
    valid: list[TouchEvent] = []
    for touch in touches:
        if touch.occurred_at > conversion_time:
            continue

        diff = conversion_time - touch.occurred_at
        if touch.event_type == "ad.impression":
            if diff <= timedelta(days=impression_lookback_days):
                valid.append(touch)
        elif touch.event_type in TOUCH_TYPES and diff <= timedelta(days=click_lookback_days):
            valid.append(touch)

    # Sort chronological ascending
    valid.sort(key=lambda t: t.occurred_at)
    return valid


def compute_attribution(
    touches: Sequence[TouchEvent],
    conversion_time: datetime,
    model: str = "last_touch",
    click_lookback_days: int = 30,
    impression_lookback_days: int = 7,
) -> list[AttributionCredit]:
    """
    Computes attribution credits for a given model.
    Models supported:
    - 'last_touch': 100% to the latest touch
    - 'first_touch': 100% to the earliest touch
    - 'position': 40% first, 40% last, 20% split equally among middle touches.
      (If 1 touch: 100%. If 2 touches: 50% / 50%).
    Credits strictly sum to 1.0.
    """
    valid_touches = filter_touches_within_lookback(
        touches, conversion_time, click_lookback_days, impression_lookback_days
    )
    if not valid_touches:
        return []

    n = len(valid_touches)
    credits: list[float] = [0.0] * n

    if model == "last_touch":
        credits[-1] = 1.0

    elif model == "first_touch":
        credits[0] = 1.0

    elif model == "position":
        if n == 1:
            credits[0] = 1.0
        elif n == 2:
            credits[0] = 0.5
            credits[1] = 0.5
        else:
            credits[0] = 0.4
            credits[-1] = 0.4
            middle_count = n - 2
            middle_share = 0.2 / middle_count
            for i in range(1, n - 1):
                credits[i] = middle_share
    else:
        raise ValueError(f"Unsupported attribution model: {model}")

    # Ensure precision normalisation
    total = sum(credits)
    if total > 0:
        credits = [c / total for c in credits]

    results: list[AttributionCredit] = []
    for touch, credit in zip(valid_touches, credits, strict=False):
        results.append(
            AttributionCredit(
                touch_event_id=touch.event_id,
                model=model,
                credit=round(credit, 4),
                match_method=touch.match_method,
                confidence=touch.confidence,
                campaign_id=touch.campaign_id,
                asset_id=touch.asset_id,
                decision_id=touch.decision_id,
            )
        )
    return results

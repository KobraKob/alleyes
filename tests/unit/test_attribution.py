"""Unit and property tests for multi-touch attribution."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from src.engine.domain.attribution import (
    TouchEvent,
    compute_attribution,
    filter_touches_within_lookback,
)


def test_last_touch_attribution() -> None:
    now = datetime.now(UTC)
    t1 = TouchEvent(event_id=uuid4(), event_type="ad.click", occurred_at=now - timedelta(days=5))
    t2 = TouchEvent(
        event_id=uuid4(), event_type="message.inbound", occurred_at=now - timedelta(days=1)
    )

    credits = compute_attribution([t1, t2], conversion_time=now, model="last_touch")
    assert len(credits) == 2
    assert credits[0].credit == 0.0
    assert credits[1].credit == 1.0


def test_first_touch_attribution() -> None:
    now = datetime.now(UTC)
    t1 = TouchEvent(event_id=uuid4(), event_type="ad.click", occurred_at=now - timedelta(days=5))
    t2 = TouchEvent(
        event_id=uuid4(), event_type="message.inbound", occurred_at=now - timedelta(days=1)
    )

    credits = compute_attribution([t1, t2], conversion_time=now, model="first_touch")
    assert len(credits) == 2
    assert credits[0].credit == 1.0
    assert credits[1].credit == 0.0


def test_position_attribution_three_touches() -> None:
    now = datetime.now(UTC)
    t1 = TouchEvent(event_id=uuid4(), event_type="ad.click", occurred_at=now - timedelta(days=6))
    t2 = TouchEvent(
        event_id=uuid4(), event_type="form.submitted", occurred_at=now - timedelta(days=3)
    )
    t3 = TouchEvent(
        event_id=uuid4(), event_type="message.inbound", occurred_at=now - timedelta(days=1)
    )

    credits = compute_attribution([t1, t2, t3], conversion_time=now, model="position")
    assert len(credits) == 3
    assert pytest.approx(credits[0].credit, abs=1e-3) == 0.4
    assert pytest.approx(credits[1].credit, abs=1e-3) == 0.2
    assert pytest.approx(credits[2].credit, abs=1e-3) == 0.4
    assert pytest.approx(sum(c.credit for c in credits), abs=1e-3) == 1.0


def test_lookback_filtering() -> None:
    now = datetime.now(UTC)
    # Click 35 days ago (outside 30-day lookback)
    t_old_click = TouchEvent(
        event_id=uuid4(), event_type="ad.click", occurred_at=now - timedelta(days=35)
    )
    # Impression 10 days ago (outside 7-day lookback)
    t_old_imp = TouchEvent(
        event_id=uuid4(), event_type="ad.impression", occurred_at=now - timedelta(days=10)
    )
    # Valid click 5 days ago
    t_valid_click = TouchEvent(
        event_id=uuid4(), event_type="ad.click", occurred_at=now - timedelta(days=5)
    )

    valid = filter_touches_within_lookback(
        [t_old_click, t_old_imp, t_valid_click], conversion_time=now
    )
    assert len(valid) == 1
    assert valid[0].event_id == t_valid_click.event_id


@hyp_settings(max_examples=200)
@given(
    touch_count=st.integers(min_value=1, max_value=10),
    model=st.sampled_from(["last_touch", "first_touch", "position"]),
)
def test_hypothesis_attribution_credits_sum_to_one(touch_count: int, model: str) -> None:
    now = datetime.now(UTC)
    touches = [
        TouchEvent(
            event_id=uuid4(),
            event_type="ad.click",
            occurred_at=now - timedelta(days=i + 1),
        )
        for i in range(touch_count)
    ]
    credits = compute_attribution(touches, conversion_time=now, model=model)
    assert len(credits) == touch_count
    total_credit = sum(c.credit for c in credits)
    assert pytest.approx(total_credit, abs=1e-2) == 1.0

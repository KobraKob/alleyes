"""Table-driven unit tests for governance rules and policy validation."""

from datetime import UTC, datetime, timedelta

import pytest

from src.engine.domain.policy import (
    evaluate_autonomy_level,
    evaluate_claims,
    evaluate_consent,
    evaluate_kill_switch,
    evaluate_whatsapp_window,
    is_in_quiet_hours,
)


def test_kill_switch_precedence() -> None:
    ok, reason = evaluate_kill_switch(engaged=True, scope="all")
    assert not ok
    assert "Kill switch engaged" in (reason or "")

    ok_off, reason_off = evaluate_kill_switch(engaged=False, scope="all")
    assert ok_off
    assert reason_off is None


@pytest.mark.parametrize(
    "has_consent,is_suppressed,expected_ok",
    [
        (True, False, True),
        (False, False, False),
        (True, True, False),
        (False, True, False),
    ],
)
def test_consent_policy_rules(has_consent: bool, is_suppressed: bool, expected_ok: bool) -> None:
    ok, _ = evaluate_consent(has_consent=has_consent, is_suppressed=is_suppressed)
    assert ok == expected_ok


def test_quiet_hours_detection() -> None:
    # 22:30 IST is in quiet hours (21:00 - 09:00)
    dt_night = datetime(2026, 10, 14, 17, 0, tzinfo=UTC)  # 22:30 IST
    assert is_in_quiet_hours(dt_night, tz_str="Asia/Kolkata")

    # 14:00 IST is daytime (outside quiet hours)
    dt_day = datetime(2026, 10, 14, 8, 30, tzinfo=UTC)  # 14:00 IST
    assert not is_in_quiet_hours(dt_day, tz_str="Asia/Kolkata")


def test_claims_regex_blocklist() -> None:
    banned = [
        r"(?i)guaranteed\s+(results|weight\s*loss)",
        r"(?i)lose\s+\d+\s*kg\s+in\s+\d+\s*days",
    ]
    ok_text = "Join our strength classes and build healthy habits with certified coaches."
    bad_text = "Guaranteed weight loss in our 30-day program!"

    ok, violations = evaluate_claims(ok_text, banned)
    assert ok
    assert len(violations) == 0

    bad_ok, bad_violations = evaluate_claims(bad_text, banned)
    assert not bad_ok
    assert len(bad_violations) > 0


def test_whatsapp_24h_window() -> None:
    now = datetime.now(UTC)
    # Template always allowed
    ok_tpl, _ = evaluate_whatsapp_window(is_template=True, last_inbound_at=None, current_time=now)
    assert ok_tpl

    # Free-form within 2 hours
    ok_recent, _ = evaluate_whatsapp_window(
        is_template=False, last_inbound_at=now - timedelta(hours=2), current_time=now
    )
    assert ok_recent

    # Free-form expired (> 24 hours)
    ok_expired, reason = evaluate_whatsapp_window(
        is_template=False, last_inbound_at=now - timedelta(hours=26), current_time=now
    )
    assert not ok_expired
    assert "template required" in (reason or "")


@pytest.mark.parametrize(
    "level,risk_tier,all_passed,expected_status,expected_approval",
    [
        (1, 1, True, "proposed", True),  # L1 always requires approval
        (2, 1, True, "approved", False),  # L2 auto-approves risk 1
        (2, 2, True, "proposed", True),  # L2 requires approval for risk 2
        (3, 2, True, "approved", False),  # L3 auto-approves
        (3, 1, False, "rejected", False),  # Failed checks always reject
    ],
)
def test_autonomy_level_decision(
    level: int, risk_tier: int, all_passed: bool, expected_status: str, expected_approval: bool
) -> None:
    status, req_approval = evaluate_autonomy_level(level, risk_tier, all_passed)
    assert status == expected_status
    assert req_approval == expected_approval

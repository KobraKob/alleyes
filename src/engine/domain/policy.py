"""Governance and policy validation engine (pure domain rules)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, tzinfo
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class PolicyEvaluationResult:
    allowed: bool
    requires_approval: bool
    status: str  # 'approved', 'rejected', 'delayed', 'proposed'
    delay_until: datetime | None = None
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)


def evaluate_kill_switch(engaged: bool, scope: str = "all") -> tuple[bool, str | None]:
    """Rule 1: Kill switch engaged halts everything."""
    if engaged:
        return False, f"Kill switch engaged for scope '{scope}'."
    return True, None


def evaluate_consent(has_consent: bool, is_suppressed: bool) -> tuple[bool, str | None]:
    """Rule 2: Outbound sends require explicit consent and no active suppression."""
    if is_suppressed:
        return False, "Recipient identifier is present on the suppressions list."
    if not has_consent:
        return False, "No active marketing consent recorded for contact."
    return True, None


def is_in_quiet_hours(
    target_dt: datetime,
    tz_str: str = "Asia/Kolkata",
    quiet_start: time = time(21, 0),
    quiet_end: time = time(9, 0),
) -> bool:
    """Rule 3: Quiet hours check in business local timezone."""
    tz: tzinfo
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = UTC

    local_dt = target_dt.astimezone(tz)
    local_time = local_dt.time()

    if quiet_start > quiet_end:
        # Crosses midnight: 21:00 to 09:00
        return local_time >= quiet_start or local_time < quiet_end
    return quiet_start <= local_time < quiet_end


def evaluate_claims(text_content: str, banned_regexes: Sequence[str]) -> tuple[bool, list[str]]:
    """Rule 6: Claims blocklist check."""
    violations: list[str] = []
    for pattern in banned_regexes:
        if re.search(pattern, text_content):
            violations.append(f"Violated claim pattern: {pattern}")
    return len(violations) == 0, violations


def evaluate_whatsapp_window(
    is_template: bool,
    last_inbound_at: datetime | None,
    current_time: datetime,
) -> tuple[bool, str | None]:
    """Rule 7: WhatsApp 24-hour customer care window."""
    if is_template:
        return True, None
    if last_inbound_at is None:
        return (
            False,
            "WhatsApp 24-hour session expired or no inbound message: approved template required.",
        )
    diff_hours = (current_time - last_inbound_at).total_seconds() / 3600.0
    if diff_hours > 24.0:
        return (
            False,
            f"Last inbound message was {diff_hours:.1f} hours ago (> 24h limit): template required.",
        )
    return True, None


def evaluate_autonomy_level(
    autonomy_level: int,
    risk_tier: int,
    all_checks_passed: bool,
) -> tuple[str, bool]:
    """
    Rule 8: Autonomy decision
    L1 -> Always requires approval (proposed)
    L2 -> Auto-approve if risk_tier == 1 and all checks passed
    L3 -> Auto-approve within caps
    """
    if not all_checks_passed:
        return "rejected", False

    if autonomy_level == 1:
        return "proposed", True

    if autonomy_level == 2:
        if risk_tier == 1:
            return "approved", False
        return "proposed", True

    if autonomy_level >= 3:
        return "approved", False

    return "proposed", True

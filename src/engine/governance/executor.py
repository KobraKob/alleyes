"""Governance executor validating policy rules and safely executing approved actions."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.engine.config import get_settings
from src.engine.connectors.email import EmailConnector
from src.engine.connectors.fake import FakeConnector
from src.engine.connectors.meta_ads import MetaAdsConnector
from src.engine.connectors.whatsapp import WhatsAppConnector
from src.engine.domain.policy import (
    evaluate_autonomy_level,
    evaluate_claims,
    evaluate_consent,
    evaluate_whatsapp_window,
    is_in_quiet_hours,
)
from src.engine.governance.kill_switch import is_kill_switch_engaged

settings = get_settings()


def execute_action(
    session: Session,
    business_id: UUID,
    action_id: UUID,
    banned_claims: list[str] | None = None,
    business_timezone: str = "Asia/Kolkata",
    override_connector: Any | None = None,
) -> dict[str, Any]:
    """
    Evaluates policy checks in strict sequence for a proposed action.
    Executes if autonomy policy allows, or keeps proposed/requires_approval.
    """
    now = datetime.now(UTC)

    # 1. Fetch action record
    act_row = session.execute(
        text("""
            SELECT id, kind, payload, risk_tier, status, proposed_at
            FROM actions
            WHERE business_id = :biz_id AND id = :act_id
        """),
        {"biz_id": str(business_id), "act_id": str(action_id)},
    ).fetchone()

    if not act_row:
        raise ValueError(f"Action {action_id} not found.")

    kind = str(act_row[1])
    payload = act_row[2] if isinstance(act_row[2], dict) else json.loads(act_row[2] or "{}")
    risk_tier = int(act_row[3])
    current_status = str(act_row[4])

    policy_results: dict[str, Any] = {}

    # Check 1: Kill Switch
    if is_kill_switch_engaged(session, business_id, scope=kind):
        policy_results["kill_switch"] = {"passed": False, "reason": "Kill switch engaged"}
        _update_action_status(
            session, business_id, action_id, "rejected", policy_results, error="Kill switch active"
        )
        return {"status": "rejected", "policy_results": policy_results}
    policy_results["kill_switch"] = {"passed": True}

    # Check 2: Consent (for outbound sends)
    contact_id_str = payload.get("contact_id")
    channel = payload.get("channel", "whatsapp")
    if kind == "send_message" and contact_id_str:
        contact_id = UUID(str(contact_id_str))
        # Query v_consent_current
        consent_row = session.execute(
            text("""
                SELECT status FROM v_consent_current
                WHERE contact_id = :c_id AND channel = :ch AND purpose = 'marketing'
            """),
            {"c_id": str(contact_id), "ch": channel},
        ).fetchone()

        has_consent = bool(consent_row and consent_row[0] == "granted")

        # Query suppressions
        supp_row = session.execute(
            text("""
                SELECT 1 FROM suppressions s
                JOIN contact_identifiers ci ON ci.value_hash = s.value_hash
                WHERE s.business_id = :biz_id AND s.channel = :ch AND ci.contact_id = :c_id
            """),
            {"biz_id": str(business_id), "ch": channel, "c_id": str(contact_id)},
        ).fetchone()
        is_suppressed = bool(supp_row)

        consent_ok, consent_reason = evaluate_consent(has_consent, is_suppressed)
        if not consent_ok:
            policy_results["consent"] = {"passed": False, "reason": consent_reason}
            _update_action_status(
                session, business_id, action_id, "rejected", policy_results, error=consent_reason
            )
            return {"status": "rejected", "policy_results": policy_results}
        policy_results["consent"] = {"passed": True}

    # Check 3: Quiet Hours (for sends)
    if kind == "send_message":
        in_quiet = is_in_quiet_hours(now, tz_str=business_timezone)
        if in_quiet:
            policy_results["quiet_hours"] = {"passed": False, "action": "delay"}
            _update_action_status(
                session,
                business_id,
                action_id,
                "proposed",
                policy_results,
                error="Delayed: currently inside local quiet hours (21:00-09:00)",
            )
            return {"status": "delayed", "policy_results": policy_results}
        policy_results["quiet_hours"] = {"passed": True}

    # Check 4: Claims check (content regex blocklist)
    content_text = payload.get("content") or payload.get("headline", "")
    if content_text and banned_claims:
        claims_ok, violations = evaluate_claims(content_text, banned_claims)
        if not claims_ok:
            reason = "; ".join(violations)
            policy_results["claims_check"] = {"passed": False, "violations": violations}
            _update_action_status(
                session, business_id, action_id, "rejected", policy_results, error=reason
            )
            return {"status": "rejected", "policy_results": policy_results}
        policy_results["claims_check"] = {"passed": True}

    # Check 5: WhatsApp 24-hour Window rule
    if kind == "send_message" and channel == "whatsapp":
        is_template = bool(payload.get("template"))
        last_inbound_row = (
            session.execute(
                text("""
                SELECT first_inbound_at FROM conversations
                WHERE contact_id = :c_id ORDER BY first_inbound_at DESC NULLS LAST LIMIT 1
            """),
                {"c_id": str(contact_id_str)},
            ).fetchone()
            if contact_id_str
            else None
        )

        last_inbound = last_inbound_row[0] if last_inbound_row else None
        wa_ok, wa_reason = evaluate_whatsapp_window(is_template, last_inbound, now)
        if not wa_ok:
            policy_results["whatsapp_window"] = {"passed": False, "reason": wa_reason}
            _update_action_status(
                session, business_id, action_id, "rejected", policy_results, error=wa_reason
            )
            return {"status": "rejected", "policy_results": policy_results}
        policy_results["whatsapp_window"] = {"passed": True}

    # Check 6: Autonomy Level & Approval Status
    autonomy_row = session.execute(
        text("""
            SELECT autonomy_level FROM autonomy_policies
            WHERE business_id = :biz_id AND action_kind = :kind
            ORDER BY effective_from DESC LIMIT 1
        """),
        {"biz_id": str(business_id), "kind": kind},
    ).fetchone()
    autonomy_level = int(autonomy_row[0]) if autonomy_row else 1  # Default L1

    status_target, requires_approval = evaluate_autonomy_level(
        autonomy_level=autonomy_level, risk_tier=risk_tier, all_checks_passed=True
    )
    policy_results["autonomy"] = {
        "level": autonomy_level,
        "requires_approval": requires_approval,
        "status_target": status_target,
    }

    if requires_approval and current_status != "approved":
        _update_action_status(
            session, business_id, action_id, "proposed", policy_results, requires_approval=True
        )
        return {"status": "proposed", "policy_results": policy_results}

    # Check 7: Execute via Connector
    connector = override_connector or _get_connector_for_action(kind, channel)
    try:
        external_ref = _dispatch_connector_action(connector, kind, payload)
        _update_action_status(
            session,
            business_id,
            action_id,
            "executed",
            policy_results,
            requires_approval=False,
            external_ref=external_ref,
        )
        return {
            "status": "executed",
            "external_ref": external_ref,
            "policy_results": policy_results,
        }
    except Exception as exc:
        _update_action_status(
            session, business_id, action_id, "failed", policy_results, error=str(exc)
        )
        return {"status": "failed", "error": str(exc), "policy_results": policy_results}


def _update_action_status(
    session: Session,
    business_id: UUID,
    action_id: UUID,
    status: str,
    policy_results: dict[str, Any],
    requires_approval: bool = True,
    external_ref: str | None = None,
    error: str | None = None,
) -> None:
    session.execute(
        text("""
            UPDATE actions
            SET status = :status,
                policy_results = :policy_res,
                requires_approval = :req_appr,
                executed_at = CASE WHEN :status = 'executed' THEN now() ELSE executed_at END,
                external_ref = COALESCE(:ext_ref, external_ref),
                error = :err
            WHERE business_id = :biz_id AND id = :act_id
        """),
        {
            "status": status,
            "policy_res": json.dumps(policy_results),
            "req_appr": requires_approval,
            "ext_ref": external_ref,
            "err": error,
            "biz_id": str(business_id),
            "act_id": str(action_id),
        },
    )

    # Append to audit_log
    session.execute(
        text("""
            INSERT INTO audit_log (business_id, actor_kind, actor_id, action, entity_type, entity_id, diff)
            VALUES (:biz_id, 'system', 'governance_executor', 'action_status_change', 'actions', :act_id, :diff)
        """),
        {
            "biz_id": str(business_id),
            "act_id": str(action_id),
            "diff": json.dumps({"status": status, "error": error}),
        },
    )


def _get_connector_for_action(kind: str, channel: str) -> Any:
    if settings.dry_run:
        return FakeConnector(provider=channel)
    if channel == "whatsapp":
        return WhatsAppConnector()
    if channel in ("meta", "meta_ads"):
        return MetaAdsConnector()
    if channel == "email":
        return EmailConnector()
    return FakeConnector(provider=channel)


def _dispatch_connector_action(connector: Any, kind: str, payload: dict[str, Any]) -> str:
    if kind == "send_message":
        res = connector.send_message(
            account=None,
            to=payload.get("to", ""),
            content=payload.get("content", ""),
            template=payload.get("template"),
        )
        return str(res.external_message_id)
    elif kind == "create_campaign":
        res = connector.create_campaign(account=None, spec=payload)
        return str(res.external_id)
    elif kind == "change_budget":
        connector.set_budget(
            account=None,
            ref=payload.get("campaign_ref", ""),
            amount_minor=int(payload.get("amount_minor", 0)),
        )
        return f"budget_updated_{payload.get('campaign_ref')}"
    elif kind == "pause_campaign":
        connector.set_status(account=None, ref=payload.get("campaign_ref", ""), status="PAUSED")
        return f"campaign_paused_{payload.get('campaign_ref')}"
    return "executed_mock_ref"

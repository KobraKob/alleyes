"""Retention-Lite Agent: Lifecycle check-ins, attendance recovery, and retention bandit loops."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import text

from src.engine.agents.base import (
    AgentContext,
    execute_structured_completion,
    load_prompt_file,
)
from src.engine.governance.actions import propose_action
from src.engine.learning.decide import decide


class RetentionMessageOutput(BaseModel):
    message_text: str
    tone: str
    action_suggested: str


def run_retention_agent(
    ctx: AgentContext,
    contact_id: UUID,
    trigger_kind: str,  # 'welcome_day0', 'checkin_day3', 'nudge_inactive_10d', 'recovery_noshow_2h'
    channel: str = "whatsapp",
) -> dict[str, Any] | None:
    """
    Executes retention check-in for a member.
    Enforces frequency rule: max 1 retention message per member per 3 days.
    Emits decide() on followup_script and proposes send_message action.
    """
    now = datetime.now(UTC)
    three_days_ago = now - timedelta(days=3)

    # 1. Frequency check: Max 1 message per 3 days
    recent_send = ctx.session.execute(
        text("""
            SELECT 1 FROM actions
            WHERE business_id = :biz_id
              AND kind = 'send_message'
              AND (payload->>'contact_id') = :c_id
              AND proposed_at >= :since
            LIMIT 1
        """),
        {"biz_id": str(ctx.business_id), "c_id": str(contact_id), "since": three_days_ago},
    ).fetchone()

    if recent_send:
        # Capped by frequency rule
        return None

    # 2. Select followup_script arm via decide()
    arm_rows = ctx.session.execute(
        text("""
            SELECT a.id FROM arms a
            JOIN decision_points dp ON dp.id = a.decision_point_id
            WHERE (a.business_id = :b OR a.business_id IS NULL)
              AND dp.key = 'followup_script'
        """),
        {"b": str(ctx.business_id)},
    ).fetchall()

    candidate_arms = [UUID(str(r[0])) for r in arm_rows]
    decision_record = None
    if candidate_arms:
        decision_record = decide(
            session=ctx.session,
            business_id=ctx.business_id,
            decision_key="followup_script",
            candidate_arm_ids=candidate_arms,
            context={"trigger": trigger_kind},
            contact_id=contact_id,
            run_id=ctx.run_id,
            pack_config=ctx.pack_config,
        )

    # 3. Generate message text
    retention_prompt_tpl, _ = load_prompt_file("retention/message.md")
    prompt = f"Member Trigger: {trigger_kind}\nGenerate a supportive, brief check-in message."

    msg_output, _, _ = execute_structured_completion(
        llm=ctx.llm,
        prompt=prompt,
        system_prompt=retention_prompt_tpl,
        output_schema=RetentionMessageOutput,
    )

    # 4. Propose send_message action
    action = propose_action(
        session=ctx.session,
        business_id=ctx.business_id,
        kind="send_message",
        payload={
            "channel": channel,
            "contact_id": str(contact_id),
            "content": msg_output.message_text,
            "decision_id": str(decision_record.id) if decision_record else None,
            "trigger": trigger_kind,
        },
        reasoning=f"Retention outreach for lifecycle milestone '{trigger_kind}'",
        risk_tier=1,
        idempotency_key=f"retention_{contact_id}_{trigger_kind}_{uuid4().hex[:6]}",
        run_id=ctx.run_id,
    )

    return {
        "status": "proposed",
        "action_id": str(action.id),
        "message_text": msg_output.message_text,
        "trigger": trigger_kind,
    }

"""Lead Response Agent: Triage, SLA-bound immediate qualification, and trial booking."""

from datetime import UTC, datetime
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


class IntentClassificationOutput(BaseModel):
    intent: str
    confidence: float
    urgency: str = "normal"


class ReplyGenerationOutput(BaseModel):
    reply_text: str
    handoff_required: bool
    proposed_action: str


def run_lead_response_agent(
    ctx: AgentContext,
    contact_id: UUID,
    conversation_id: UUID,
    inbound_message_text: str,
    channel: str = "whatsapp",
    inbound_timestamp: datetime | None = None,
) -> dict[str, Any]:
    """
    Executes the lead response workflow:
    1. Classifies intent.
    2. Checks for handoff triggers.
    3. Selects lead_first_reply style via decide().
    4. Generates grounded reply.
    5. Proposes send_message action and updates conversation response SLA.
    """
    now = datetime.now(UTC)
    inbound_at = inbound_timestamp or now

    # Load prompts
    intent_prompt_tpl, _ = load_prompt_file("lead_response/intent.md")
    reply_prompt_tpl, _ = load_prompt_file("lead_response/reply.md")

    # Step 1: Classify Intent
    intent_result, in_tokens_1, out_tokens_1 = execute_structured_completion(
        llm=ctx.llm,
        prompt=f"Customer Message: '{inbound_message_text}'",
        system_prompt=intent_prompt_tpl,
        output_schema=IntentClassificationOutput,
    )

    # Step 2: Check for immediate handoff triggers
    is_handoff = False
    lower_msg = inbound_message_text.lower()
    if intent_result.intent in ("complaint", "handoff") or any(
        term in lower_msg
        for term in ("human", "person", "manager", "injury", "medical", "doctor", "discount")
    ):
        is_handoff = True

    if is_handoff:
        # Mark conversation as handed_off
        ctx.session.execute(
            text("""
                UPDATE conversations
                SET status = 'handed_off'
                WHERE business_id = :biz_id AND id = :conv_id
            """),
            {"biz_id": str(ctx.business_id), "conv_id": str(conversation_id)},
        )
        return {"status": "handed_off", "intent": intent_result.intent, "action": "human_handoff"}

    # Step 3: Choose lead_first_reply arm via decide()
    # Query candidate arms for lead_first_reply
    arm_rows = ctx.session.execute(
        text("""
            SELECT a.id FROM arms a
            JOIN decision_points dp ON dp.id = a.decision_point_id
            WHERE (a.business_id = :biz_id OR a.business_id IS NULL)
              AND dp.key = 'lead_first_reply'
        """),
        {"biz_id": str(ctx.business_id)},
    ).fetchall()

    candidate_arm_ids = [UUID(str(r[0])) for r in arm_rows]
    decision_record = None

    if candidate_arm_ids:
        decision_record = decide(
            session=ctx.session,
            business_id=ctx.business_id,
            decision_key="lead_first_reply",
            candidate_arm_ids=candidate_arm_ids,
            context={"channel": channel, "intent": intent_result.intent},
            contact_id=contact_id,
            run_id=ctx.run_id,
            pack_config=ctx.pack_config,
        )

    # Step 4: Generate grounded reply
    facts_str = f"Brand Facts: {ctx.brand_profile.get('usps', 'Indiranagar branch, open 6am-10pm, free 7-day trial')}"
    reply_prompt = (
        f"{facts_str}\n"
        f"Customer Message: '{inbound_message_text}'\n"
        f"Customer Intent: {intent_result.intent}"
    )

    reply_result, in_tokens_2, out_tokens_2 = execute_structured_completion(
        llm=ctx.llm,
        prompt=reply_prompt,
        system_prompt=reply_prompt_tpl,
        output_schema=ReplyGenerationOutput,
    )

    if reply_result.handoff_required:
        ctx.session.execute(
            text("""
                UPDATE conversations SET status = 'handed_off'
                WHERE business_id = :biz_id AND id = :conv_id
            """),
            {"biz_id": str(ctx.business_id), "conv_id": str(conversation_id)},
        )
        return {"status": "handed_off", "reply": reply_result.reply_text}

    # Step 5: Propose action to send message
    idemp_key = f"lead_reply_{conversation_id}_{uuid4().hex[:8]}"
    action_record = propose_action(
        session=ctx.session,
        business_id=ctx.business_id,
        kind="send_message",
        payload={
            "channel": channel,
            "contact_id": str(contact_id),
            "conversation_id": str(conversation_id),
            "content": reply_result.reply_text,
            "decision_id": str(decision_record.id) if decision_record else None,
        },
        reasoning=f"Automated reply addressing lead intent '{intent_result.intent}'",
        risk_tier=1,
        idempotency_key=idemp_key,
        run_id=ctx.run_id,
    )

    # Step 6: Record SLA timestamp on conversation
    ctx.session.execute(
        text("""
            UPDATE conversations
            SET first_inbound_at = COALESCE(first_inbound_at, :inbound_at),
                first_response_at = now()
            WHERE business_id = :biz_id AND id = :conv_id
        """),
        {"inbound_at": inbound_at, "biz_id": str(ctx.business_id), "conv_id": str(conversation_id)},
    )

    return {
        "status": "proposed",
        "action_id": str(action_record.id),
        "reply_text": reply_result.reply_text,
        "intent": intent_result.intent,
        "decision_id": str(decision_record.id) if decision_record else None,
    }

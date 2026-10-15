"""Interactive demo script showing the full end-to-end autonomous flow in dry-run mode."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.agents.base import execute_structured_completion, load_prompt_file
from src.engine.agents.lead_response import (
    IntentClassificationOutput,
    ReplyGenerationOutput,
)
from src.engine.config import get_settings
from src.engine.connectors.fake import FakeConnector
from src.engine.domain.attribution import TouchEvent, compute_attribution
from src.engine.domain.bandits import ArmPosterior, select_arm, update_beta_posterior
from src.engine.domain.policy import (
    evaluate_claims,
    evaluate_whatsapp_window,
    is_in_quiet_hours,
)
from src.engine.domain.rewards import ConversionContribution, compute_normalized_reward
from src.engine.llm import FakeLLMClient, get_llm_client


def run_full_flow_demo() -> None:
    print("=" * 70)
    print("  AUTONOMOUS MARKETING ENGINE: COMPLETE END-TO-END DEMO (DRY-RUN)")
    print("=" * 70)

    settings = get_settings()
    now = datetime.now(UTC)
    customer_phone = "+919876543210"
    inbound_text = (
        "Hi, I live in Indiranagar. How much is your monthly membership and can I try a workout?"
    )

    print("\n[1] NEW INBOUND WHATSAPP LEAD")
    print(f"    From: {customer_phone}")
    print(f"    Message: '{inbound_text}'")

    # Step 2: Agent runtime & intent classification with Groq / configured LLM
    print("\n[2] LEAD RESPONSE AGENT (SLA Target < 60s)")
    llm = get_llm_client() if settings.groq_api_key else FakeLLMClient()
    model_name = getattr(llm, "default_model", "mock-agent")
    print(f"    Active LLM Provider: {type(llm).__name__} (Model: {model_name})")

    intent_tpl, _ = load_prompt_file("lead_response/intent.md")
    reply_tpl, _ = load_prompt_file("lead_response/reply.md")

    intent_res, t_in1, t_out1 = execute_structured_completion(
        llm=llm,
        prompt=f"Customer Message: '{inbound_text}'",
        system_prompt=intent_tpl,
        output_schema=IntentClassificationOutput,
    )
    print(f"    Classified Intent: {intent_res.intent} (Confidence: {intent_res.confidence})")
    print(f"    Tokens Used: {t_in1} in / {t_out1} out")

    # Step 3: Bandit choice for opening response
    print("\n[3] DECIDE() API - THOMPSON POSTERIOR SAMPLING")
    candidate_arms = [
        ArmPosterior(arm_id=uuid4(), alpha=12.0, beta=18.0, n=30),  # Friendly coach
        ArmPosterior(arm_id=uuid4(), alpha=8.0, beta=22.0, n=30),  # Direct scheduler
    ]
    bandit_choice = select_arm(candidate_arms, epsilon=0.05, num_draws=2000)
    print(f"    Chosen Arm ID: {bandit_choice.chosen_arm_id}")
    print(
        f"    Exact Logged Propensity: {bandit_choice.propensity:.4f} (Explored: {bandit_choice.explored})"
    )

    # Step 4: Grounded reply generation via Groq
    reply_res, t_in2, t_out2 = execute_structured_completion(
        llm=llm,
        prompt=f"Brand Facts: Indiranagar branch, free 7-day trial. Message: '{inbound_text}'",
        system_prompt=reply_tpl,
        output_schema=ReplyGenerationOutput,
    )
    print(f"    Generated Reply: '{reply_res.reply_text}'")
    print(
        f"    Action Proposed: {reply_res.proposed_action} (Handoff Required: {reply_res.handoff_required})"
    )

    # Step 5: Governance policy checks & Action proposal
    print("\n[4] GOVERNANCE LAYER: POLICY PIPELINE CHECKS")
    in_quiet = is_in_quiet_hours(now, tz_str="Asia/Kolkata")
    print(f"    Quiet Hours Check: {'DELAY' if in_quiet else 'PASSED'}")

    claims_ok, _violations = evaluate_claims(
        reply_res.reply_text, banned_regexes=[r"(?i)guaranteed\s+results", r"(?i)lose\s+\d+\s*kg"]
    )
    print(f"    Claims Check: {'PASSED' if claims_ok else 'FAILED'}")

    wa_ok, _ = evaluate_whatsapp_window(is_template=False, last_inbound_at=now, current_time=now)
    print(f"    WhatsApp 24h Window Check: {'PASSED' if wa_ok else 'FAILED'}")

    # Action execution via connector
    fake_conn = FakeConnector(provider="whatsapp")
    send_res = fake_conn.send_message(account=None, to=customer_phone, content=reply_res.reply_text)
    print(f"    Action Dispatched: status=executed, ref={send_res.external_message_id}")

    # Step 6: Downstream Funnel Progression
    print("\n[5] EVENT-SOURCED DOWNSTREAM FUNNEL PROGRESSION")
    print("    -> [Event] form.submitted (Lead stage reached)")
    print("    -> [Event] trial.booked (Lag: +1 day)")
    print("    -> [Event] trial.attended (Lag: +3 days)")
    print("    -> [Event] membership.purchased (Lag: +7 days, Value: INR 3,500)")

    # Step 7: Multi-touch attribution
    camp_id = uuid4()
    print("\n[6] MULTI-TOUCH ATTRIBUTION COMPUTATION")
    touch_events = [
        TouchEvent(
            event_id=uuid4(),
            event_type="ad.click",
            occurred_at=now - timedelta(days=8),
            campaign_id=camp_id,
            decision_id=bandit_choice.chosen_arm_id,
        ),
        TouchEvent(
            event_id=uuid4(),
            event_type="form.submitted",
            occurred_at=now - timedelta(days=7),
            campaign_id=camp_id,
        ),
        TouchEvent(
            event_id=uuid4(),
            event_type="message.inbound",
            occurred_at=now - timedelta(days=6),
        ),
    ]
    conversion_time = now

    for model in ("last_touch", "first_touch", "position"):
        credits = compute_attribution(touch_events, conversion_time, model=model)
        credit_str = ", ".join(
            [f"touch {i + 1}: {c.credit * 100:.0f}%" for i, c in enumerate(credits)]
        )
        print(f"    Model '{model}': {credit_str} (Sum = {sum(c.credit for c in credits):.2f})")

    # Step 8: Reward calculation
    print("\n[7] REWARD COMPUTATION & BANDIT STATS DELTA UPDATE")
    contributions = [
        ConversionContribution(
            conversion_id=uuid4(), stage_key="trial_booked", reward_weight=1.0, credit=0.4
        ),
        ConversionContribution(
            conversion_id=uuid4(), stage_key="trial_attended", reward_weight=3.0, credit=0.4
        ),
        ConversionContribution(
            conversion_id=uuid4(), stage_key="member", reward_weight=10.0, credit=0.4
        ),
    ]
    norm_reward, components = compute_normalized_reward(contributions, max_stage_weight=25.0)
    print(f"    Normalized Reward Signal: {norm_reward:.4f} (Breakdown: {components})")

    # Step 9: Posterior Delta Update
    cur_a, cur_b = 12.0, 18.0
    new_a, new_b = update_beta_posterior(
        current_alpha=cur_a,
        current_beta=cur_b,
        current_applied_reward=0.0,
        new_cumulative_reward=norm_reward,
        first_time=True,
    )
    print(
        f"    Bandit Posterior Updated: Beta({cur_a:.1f}, {cur_b:.1f}) -> Beta({new_a:.2f}, {new_b:.2f})"
    )
    print(
        f"    Posterior Mean Lift: {cur_a / (cur_a + cur_b):.3f} -> {new_a / (new_a + new_b):.3f}"
    )

    print("\n" + "=" * 70)
    print("  DEMO COMPLETE: THE AUTONOMOUS FEEDBACK LOOP IS FULLY CLOSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_full_flow_demo()

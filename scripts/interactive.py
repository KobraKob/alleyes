"""Interactive CLI to test customer messages against Groq LLM, Bandits, and Governance."""

import sys
from datetime import UTC, datetime
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
from src.engine.domain.bandits import ArmPosterior, select_arm, update_beta_posterior
from src.engine.domain.policy import (
    evaluate_autonomy_level,
    evaluate_claims,
    evaluate_whatsapp_window,
    is_in_quiet_hours,
)
from src.engine.llm import get_llm_client


def process_message(user_message: str) -> None:
    settings = get_settings()
    llm = get_llm_client()
    now = datetime.now(UTC)

    print("\n" + "=" * 70)
    print(f'  CUSTOMER MESSAGE: "{user_message}"')
    print("=" * 70)

    # 1. Intent Classification
    intent_tpl, _ = load_prompt_file("lead_response/intent.md")
    reply_tpl, _ = load_prompt_file("lead_response/reply.md")

    print("\n[1] GROQ INTENT CLASSIFICATION")
    intent_res, t_in1, t_out1 = execute_structured_completion(
        llm=llm,
        prompt=f"Customer Message: '{user_message}'",
        system_prompt=intent_tpl,
        output_schema=IntentClassificationOutput,
    )
    print(f"    Intent:     {intent_res.intent.upper()}")
    print(f"    Confidence: {intent_res.confidence}%")
    print(f"    Urgency:    {intent_res.urgency.upper()}")
    print(f"    Latency:    Groq ({settings.llm_model}) -> {t_in1} in / {t_out1} out tokens")

    # 2. Multi-Armed Bandit Arm Selection
    print("\n[2] BAYESIAN THOMPSON SAMPLING (DECIDE)")
    candidate_arms = [
        ArmPosterior(arm_id=uuid4(), alpha=15.0, beta=10.0, n=25),  # Arm A: Free 7-Day Trial Hook
        ArmPosterior(
            arm_id=uuid4(), alpha=9.0, beta=16.0, n=25
        ),  # Arm B: Direct Trainer Consultation
        ArmPosterior(
            arm_id=uuid4(), alpha=12.0, beta=13.0, n=25
        ),  # Arm C: 20% Off Annual Membership
    ]
    arm_labels = {
        candidate_arms[0].arm_id: "Arm A: Free 7-Day Trial Hook",
        candidate_arms[1].arm_id: "Arm B: Direct Trainer Consultation",
        candidate_arms[2].arm_id: "Arm C: 20% Off Annual Membership",
    }
    choice = select_arm(candidate_arms, epsilon=0.05, num_draws=2000)
    chosen_label = arm_labels[choice.chosen_arm_id]
    print(f"    Winning Arm:  {chosen_label}")
    print(f"    Propensity:   {choice.propensity * 100:.2f}% (Explored: {choice.explored})")

    # 3. Grounded Reply Generation
    print("\n[3] GROQ GROUNDED RESPONSE GENERATION")
    brand_context = (
        "Brand: Iron Fitness Gym Bangalore. "
        "Locations: Indiranagar (6am-10pm), Koramangala (6am-11pm), HSR Layout (6am-10pm). "
        "Offers: Free 7-day trial passes available. Monthly INR 3,500, Annual INR 24,000. "
        f"Selected Strategy: {chosen_label}."
    )
    reply_res, t_in2, t_out2 = execute_structured_completion(
        llm=llm,
        prompt=f"Brand Context: {brand_context}\nCustomer Message: '{user_message}'",
        system_prompt=reply_tpl,
        output_schema=ReplyGenerationOutput,
    )
    print(f'    Generated Reply:\n    "{reply_res.reply_text}"')
    print(f"    Handoff Needed: {reply_res.handoff_required}")
    print(f"    Action:         {reply_res.proposed_action}")

    # 4. Governance Policy Checks
    print("\n[4] GOVERNANCE & REGULATORY POLICY PIPELINE")
    in_quiet = is_in_quiet_hours(now, tz_str="Asia/Kolkata")
    print(
        f"    TRAI Quiet Hours (21:00-09:00 IST): {'DELAY (Outside permitted hours)' if in_quiet else 'PASSED'}"
    )

    claims_ok, violations = evaluate_claims(
        reply_res.reply_text,
        banned_regexes=[
            r"(?i)guaranteed\s+results",
            r"(?i)lose\s+\d+\s*kg",
            r"(?i)permanent\s+cure",
        ],
    )
    print(
        f"    Claims Blocklist Check:             {'FAILED: ' + str(violations) if not claims_ok else 'PASSED'}"
    )

    wa_ok, wa_reason = evaluate_whatsapp_window(
        is_template=False, last_inbound_at=now, current_time=now
    )
    print(
        f"    WhatsApp 24h Window Check:          {'PASSED' if wa_ok else 'FAILED: ' + str(wa_reason)}"
    )

    # 5. Autonomy Level & Dispatch
    print("\n[5] AUTONOMY EVALUATION")
    all_passed = (not in_quiet) and claims_ok and wa_ok
    status, req_approval = evaluate_autonomy_level(
        autonomy_level=2, risk_tier=1, all_checks_passed=all_passed
    )
    print("    Autonomy Level:   L2 (Standard Conversational Replies)")
    print(f"    Execution Status: {status.upper()}")
    print(f"    Human Approval:   {'REQUIRED' if req_approval else 'AUTO-APPROVED'}")

    # 6. Posterior Learning Update
    print("\n[6] BAYESIAN LEARNING FEEDBACK")
    simulated_reward = 0.85
    new_alpha, new_beta = update_beta_posterior(
        current_alpha=15.0,
        current_beta=10.0,
        current_applied_reward=0.0,
        new_cumulative_reward=simulated_reward,
        first_time=True,
    )
    print(f"    Posterior Updated: Beta(15.0, 10.0) -> Beta({new_alpha:.2f}, {new_beta:.2f})")
    print(
        f"    Expected Arm Conversion Rate: {15.0 / 25.0:.3f} -> {new_alpha / (new_alpha + new_beta):.3f}"
    )
    print("=" * 70 + "\n")


def main() -> None:
    if len(sys.argv) > 1:
        # One-shot CLI message
        msg = " ".join(sys.argv[1:])
        process_message(msg)
        return

    # Interactive prompt loop
    print("=" * 70)
    print("  AUTONOMOUS MARKETING ENGINE - LIVE INTERACTIVE RUNNER")
    print("  Powered by Groq LLM & Thompson Sampling Bandit")
    print("=" * 70)
    print("Type any customer query (e.g. 'Can I book a free trial at Indiranagar?')")
    print("Type 'exit' or 'quit' to end.\n")

    default_samples = [
        "Hi, can I book a free trial workout at your Indiranagar gym tomorrow morning?",
        "How much is your annual membership and do you have EMI options?",
        "I need to cancel my membership immediately, please help.",
    ]

    print("Sample queries you can try:")
    for idx, sample in enumerate(default_samples, 1):
        print(f"  [{idx}] {sample}")
    print()

    while True:
        try:
            user_input = input("Enter query [or 1-3 for sample, 'exit' to quit]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input or user_input.lower() in ("exit", "quit", "q"):
            print("Goodbye!")
            break

        if user_input in ("1", "2", "3"):
            user_input = default_samples[int(user_input) - 1]

        process_message(user_input)


if __name__ == "__main__":
    main()

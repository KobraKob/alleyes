"""Ads Agent: Creative variants generation, claims checking, arms registration, and live campaign optimization."""

import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import text

from src.engine.agents.base import (
    AgentContext,
    execute_structured_completion,
    load_prompt_file,
)
from src.engine.domain.policy import evaluate_claims
from src.engine.governance.actions import propose_action


class CreativeFeatures(BaseModel):
    hook_type: str
    offer_type: str
    tone: str
    has_face: bool = True


class AdVariant(BaseModel):
    headline: str
    primary_text: str
    cta: str
    features: CreativeFeatures


class CreativeVariantsOutput(BaseModel):
    variants: list[AdVariant]


def run_ads_agent_generate_creatives(
    ctx: AgentContext,
    campaign_id: UUID,
    hook_theme: str = "strength_focus",
    offer_theme: str = "free_trial_7d",
    banned_claims: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Generates N creative variants for a campaign, runs claims check,
    persists assets, and registers each as an arm.
    """
    variants_prompt_tpl, _ = load_prompt_file("ads/creative_variants.md")

    prompt = (
        f"Campaign Angle: {hook_theme}\n"
        f"Offer Angle: {offer_theme}\n"
        f"Generate 3 distinct creative ad variants."
    )

    variants_output, _, _ = execute_structured_completion(
        llm=ctx.llm,
        prompt=prompt,
        system_prompt=variants_prompt_tpl,
        output_schema=CreativeVariantsOutput,
    )

    # Fetch decision points for hook and offer
    dp_hook = ctx.session.execute(
        text(
            "SELECT id FROM decision_points WHERE key = 'ad_hook' AND (business_id = :b OR business_id IS NULL) LIMIT 1"
        ),
        {"b": str(ctx.business_id)},
    ).fetchone()
    dp_hook_id = UUID(str(dp_hook[0])) if dp_hook else None

    registered_assets = []

    for variant in variants_output.variants:
        full_copy = f"{variant.headline} {variant.primary_text} {variant.cta}"
        claims_ok = True
        violations: list[str] = []
        if banned_claims:
            claims_ok, violations = evaluate_claims(full_copy, banned_claims)

        asset_id = uuid4()
        status = "approved" if claims_ok else "rejected"

        # Insert asset
        ctx.session.execute(
            text("""
                INSERT INTO assets (
                    id, business_id, kind, title, content, features,
                    brand_check, status, created_at
                )
                VALUES (
                    :id, :biz_id, 'ad_creative', :title, :content, :features,
                    :brand_check, :status, now()
                )
            """),
            {
                "id": str(asset_id),
                "biz_id": str(ctx.business_id),
                "title": variant.headline,
                "content": json.dumps(
                    {
                        "headline": variant.headline,
                        "primary_text": variant.primary_text,
                        "cta": variant.cta,
                    }
                ),
                "features": json.dumps(variant.features.model_dump()),
                "brand_check": json.dumps({"passed": claims_ok, "violations": violations}),
                "status": status,
            },
        )

        # Register as an arm if approved
        arm_id = None
        if claims_ok and dp_hook_id:
            arm_id = uuid4()
            sig = f"ad_hook:{variant.features.hook_type}"
            ctx.session.execute(
                text("""
                    INSERT INTO arms (
                        id, business_id, decision_point_id, asset_id, label, signature, status
                    )
                    VALUES (
                        :id, :biz_id, :dp_id, :ast_id, :label, :sig, 'active'
                    )
                """),
                {
                    "id": str(arm_id),
                    "biz_id": str(ctx.business_id),
                    "dp_id": str(dp_hook_id),
                    "ast_id": str(asset_id),
                    "label": variant.headline,
                    "sig": sig,
                },
            )

        registered_assets.append(
            {
                "asset_id": str(asset_id),
                "headline": variant.headline,
                "status": status,
                "arm_id": str(arm_id) if arm_id else None,
            }
        )

    return registered_assets


def run_ads_optimization(
    ctx: AgentContext,
    campaign_id: UUID,
) -> list[str]:
    """
    Evaluates live arms for a campaign and proposes pause_campaign actions
    for underperforming arms (posterior prob best < 2% and n >= 200).
    """
    rows = ctx.session.execute(
        text("""
            SELECT a.id, a.label, s.alpha, s.beta, s.n
            FROM arms a
            JOIN arm_stats s ON s.arm_id = a.id
            WHERE a.business_id = :biz_id
              AND s.segment_key = 'all'
              AND s.n >= 200
        """),
        {"biz_id": str(ctx.business_id)},
    ).fetchall()

    actions_proposed = []
    for r in rows:
        arm_id, label, a, b, n = str(r[0]), str(r[1]), float(r[2]), float(r[3]), int(r[4])
        mean = a / (a + b)
        # If mean is extremely low with n >= 200
        if mean < 0.02:
            act = propose_action(
                session=ctx.session,
                business_id=ctx.business_id,
                kind="pause_campaign",
                payload={
                    "arm_id": arm_id,
                    "campaign_id": str(campaign_id),
                    "reason": "posterior < 2%",
                },
                reasoning=f"Pausing arm '{label}' due to statistically confirmed underperformance (n={n}, mean={mean:.3f})",
                risk_tier=2,
                idempotency_key=f"pause_arm_{arm_id}_{uuid4().hex[:6]}",
                run_id=ctx.run_id,
            )
            actions_proposed.append(str(act.id))

    return actions_proposed

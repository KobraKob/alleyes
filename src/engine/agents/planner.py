"""Planner Agent: Formulates weekly acquisition plans respecting capacity and hard budget/CAC constraints."""

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


class TargetArmsModel(BaseModel):
    ad_hook: str
    offer: str
    audience: str


class CampaignProposal(BaseModel):
    name: str
    location_id: str | None = None
    channel: str = "meta_ads"
    budget_minor: int
    hypothesis: str
    target_arms: TargetArmsModel | None = None


class WeeklyPlanOutput(BaseModel):
    summary: str
    campaigns: list[CampaignProposal]


def run_planner_agent(
    ctx: AgentContext,
    objective_id: UUID,
) -> dict[str, Any]:
    """
    Formulates a weekly plan:
    Reads historical performance, locations, constraints.
    Validates hard code constraints (total budget <= objective budget, CAC <= max_cac).
    Proposes 'create_campaign' actions (status pending_approval).
    """
    # 1. Fetch objective
    obj_row = ctx.session.execute(
        text("""
            SELECT statement, budget_minor, constraints, target_value
            FROM objectives
            WHERE business_id = :biz_id AND id = :obj_id
        """),
        {"biz_id": str(ctx.business_id), "obj_id": str(objective_id)},
    ).fetchone()

    if not obj_row:
        raise ValueError(f"Objective {objective_id} not found.")

    statement, total_budget_minor, constraints, target_value = (
        str(obj_row[0]),
        int(obj_row[1]),
        obj_row[2] if isinstance(obj_row[2], dict) else {},
        float(obj_row[3]),
    )
    max_cac_minor = constraints.get("max_cac_minor", 150000)

    # 2. Fetch locations
    loc_rows = ctx.session.execute(
        text("SELECT id, name, capacity_per_day FROM locations WHERE business_id = :biz_id"),
        {"biz_id": str(ctx.business_id)},
    ).fetchall()
    locations_summary = [{"id": str(r[0]), "name": r[1], "capacity": r[2]} for r in loc_rows]

    # 3. Fetch active insights
    insight_rows = ctx.session.execute(
        text("""
            SELECT statement, confidence FROM playbook_insights
            WHERE business_id = :biz_id AND status IN ('supported', 'hypothesis')
              AND (expires_at IS NULL OR expires_at > now())
        """),
        {"biz_id": str(ctx.business_id)},
    ).fetchall()
    insights_summary = [{"statement": r[0], "confidence": float(r[1])} for r in insight_rows]

    # Load prompt
    planner_prompt_tpl, _ = load_prompt_file("planner/weekly_plan.md")

    prompt_input = (
        f"Objective: {statement}\n"
        f"Budget Minor: {total_budget_minor} paise\n"
        f"Max CAC Minor: {max_cac_minor} paise\n"
        f"Locations: {locations_summary}\n"
        f"Playbook Insights: {insights_summary}\n"
    )

    plan_output, _, _ = execute_structured_completion(
        llm=ctx.llm,
        prompt=prompt_input,
        system_prompt=planner_prompt_tpl,
        output_schema=WeeklyPlanOutput,
    )

    # CODE VALIDATION OF HARD CONSTRAINTS (NOT TRUSTING LLM)
    proposed_total_budget = sum(c.budget_minor for c in plan_output.campaigns)
    if proposed_total_budget > total_budget_minor:
        raise ValueError(
            f"Planner constraint violation: Proposed budget ({proposed_total_budget}) "
            f"exceeds objective budget ({total_budget_minor})."
        )

    # Estimate proposed CAC = budget / target_value
    estimated_cac = proposed_total_budget / max(1.0, target_value)
    if estimated_cac > max_cac_minor:
        raise ValueError(
            f"Planner constraint violation: Estimated CAC ({estimated_cac:.0f}) "
            f"exceeds constraint max_cac ({max_cac_minor})."
        )

    # Create proposed actions for each campaign
    created_actions = []
    for camp in plan_output.campaigns:
        action = propose_action(
            session=ctx.session,
            business_id=ctx.business_id,
            kind="create_campaign",
            payload={
                "name": camp.name,
                "channel": camp.channel,
                "budget_minor": camp.budget_minor,
                "location_id": camp.location_id,
                "hypothesis": camp.hypothesis,
                "target_arms": camp.target_arms.model_dump() if camp.target_arms else {},
                "objective_id": str(objective_id),
            },
            reasoning=camp.hypothesis,
            risk_tier=2,  # Level 2 risk tier
            idempotency_key=f"plan_camp_{objective_id}_{uuid4().hex[:8]}",
            run_id=ctx.run_id,
        )
        created_actions.append(str(action.id))

    return {
        "status": "planned",
        "summary": plan_output.summary,
        "actions": created_actions,
        "total_budget_minor": proposed_total_budget,
    }

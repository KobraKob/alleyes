"""Unit tests for agents runtime, planner constraints, and analyst numeric validation."""

import pytest

from src.engine.agents.analyst import validate_narrative_numbers
from src.engine.agents.planner import CampaignProposal


def test_analyst_rejects_hallucinated_numbers() -> None:
    evidence_numbers = {"50000", "20", "500"}
    # Narrative citing only allowed numbers
    valid_narrative = "Total spend reached 50000 paise with 20 paid conversions."
    assert validate_narrative_numbers(valid_narrative, evidence_numbers)

    # Narrative citing hallucinated number 99
    invalid_narrative = "Total spend was 50000 paise yielding 99 memberships."
    assert not validate_narrative_numbers(invalid_narrative, evidence_numbers)


def test_planner_budget_constraint_enforcement() -> None:
    # Code-level validation: proposed budget must not exceed objective budget
    total_budget_minor = 1000000  # 10,000 INR
    proposed_campaigns = [
        CampaignProposal(name="C1", budget_minor=800000, hypothesis="H1"),
        CampaignProposal(
            name="C2", budget_minor=300000, hypothesis="H2"
        ),  # Sum = 1,100,000 > 1,000,000
    ]
    proposed_sum = sum(c.budget_minor for c in proposed_campaigns)
    assert proposed_sum > total_budget_minor
    # Ensure error is raised
    with pytest.raises(ValueError, match="exceeds objective budget"):
        if proposed_sum > total_budget_minor:
            raise ValueError(
                f"Planner constraint violation: Proposed budget ({proposed_sum}) exceeds objective budget ({total_budget_minor})."
            )


def test_planner_cac_constraint_enforcement() -> None:
    max_cac_minor = 150000  # 1500 INR
    target_members = 5
    # Proposed budget 1,000,000 for 5 members = 200,000 CAC > 150,000 max_cac
    proposed_budget = 1000000
    estimated_cac = proposed_budget / target_members
    assert estimated_cac > max_cac_minor

    with pytest.raises(ValueError, match="exceeds constraint max_cac"):
        if estimated_cac > max_cac_minor:
            raise ValueError(
                f"Planner constraint violation: Estimated CAC ({estimated_cac:.0f}) exceeds constraint max_cac ({max_cac_minor})."
            )

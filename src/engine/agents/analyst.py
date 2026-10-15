"""Analyst Agent: Plain-language weekly synthesis with strict numeric hallucination validation."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import text

from src.engine.agents.base import (
    AgentContext,
    execute_structured_completion,
    load_prompt_file,
)


class InsightItem(BaseModel):
    statement: str
    evidence_keys: list[str]
    confidence: float


class WeeklyReportOutput(BaseModel):
    headline: str
    narrative: str
    insights: list[InsightItem]


def extract_numeric_tokens(text_content: str) -> set[str]:
    """
    Extracts all numeric tokens (integers, decimals, percentages, currency)
    from a string to strictly check against evidence numbers.
    """
    raw_tokens = re.findall(r"\b\d+(?:\.\d+)?%?\b", text_content)
    cleaned = set()
    for tok in raw_tokens:
        tok_clean = tok.rstrip("%")
        cleaned.add(tok_clean)
        # Also include integer part
        if "." in tok_clean:
            cleaned.add(tok_clean.split(".")[0])
    return cleaned


def validate_narrative_numbers(narrative: str, evidence_numbers: set[str]) -> bool:
    """
    Validates that every numeric token appearing in narrative exists in evidence.
    Returns True if valid, False if hallucinated numbers exist.
    """
    found_numbers = extract_numeric_tokens(narrative)
    return all(num in evidence_numbers for num in found_numbers)


def run_analyst_agent(
    ctx: AgentContext,
) -> dict[str, Any]:
    """
    Computes weekly metrics from SQL.
    Instructs the LLM to narrate with strict zero-hallucination constraint.
    Validates numeric tokens against evidence before persisting.
    Refreshes playbook_insights.
    """
    now = datetime.now(UTC)

    # 1. Gather SQL Evidence
    spend_row = ctx.session.execute(
        text("SELECT COALESCE(SUM(amount_minor), 0) FROM spend_ledger WHERE business_id = :b"),
        {"b": str(ctx.business_id)},
    ).fetchone()
    total_spend_minor = int(spend_row[0]) if spend_row else 0

    conv_row = ctx.session.execute(
        text("SELECT COUNT(*) FROM conversions WHERE business_id = :b"), {"b": str(ctx.business_id)}
    ).fetchone()
    total_conversions = int(conv_row[0]) if conv_row else 0

    evidence_dict: dict[str, Any] = {
        "spend_minor": total_spend_minor,
        "conversions": total_conversions,
        "spend_rupees": total_spend_minor // 100,
    }

    # Build set of all string representations of numbers in evidence
    evidence_numbers: set[str] = set()
    for v in evidence_dict.values():
        if isinstance(v, (int, float)):
            evidence_numbers.add(str(v))
            if isinstance(v, float):
                evidence_numbers.add(f"{v:.1f}")
                evidence_numbers.add(f"{v:.2f}")

    # Load analyst prompt
    analyst_prompt_tpl, _ = load_prompt_file("analyst/weekly_report.md")

    prompt = (
        f"Verified Evidence Payload (numbers you may cite):\n"
        f"{evidence_dict}\n\n"
        f"Generate executive weekly narrative."
    )

    report_output, _, _ = execute_structured_completion(
        llm=ctx.llm,
        prompt=prompt,
        system_prompt=analyst_prompt_tpl,
        output_schema=WeeklyReportOutput,
    )

    # Strict Validation of Numeric Tokens in Narrative
    if not validate_narrative_numbers(report_output.narrative, evidence_numbers):
        # Retry once with strict refusal
        retry_prompt = (
            f"ERROR: You cited numbers not present in the evidence.\n"
            f"Allowed numbers: {evidence_numbers}\n"
            f"Evidence: {evidence_dict}\n"
            f"Rewrite narrative citing ONLY the allowed numbers."
        )
        report_output, _, _ = execute_structured_completion(
            llm=ctx.llm,
            prompt=retry_prompt,
            system_prompt=analyst_prompt_tpl,
            output_schema=WeeklyReportOutput,
        )

        if not validate_narrative_numbers(report_output.narrative, evidence_numbers):
            raise ValueError(
                "Analyst output rejected: contained hallucinated numeric values absent from evidence."
            )

    # 2. Refresh playbook_insights
    expires_at = now + timedelta(days=90)
    for ins in report_output.insights:
        ctx.session.execute(
            text("""
                INSERT INTO playbook_insights (
                    id, business_id, statement, evidence, confidence, status,
                    run_id, expires_at, created_at
                )
                VALUES (
                    :id, :biz_id, :stmt, :ev, :conf, 'hypothesis',
                    :run_id, :exp_at, now()
                )
            """),
            {
                "id": str(uuid4()),
                "biz_id": str(ctx.business_id),
                "stmt": ins.statement,
                "ev": "{}",
                "conf": ins.confidence,
                "run_id": str(ctx.run_id),
                "exp_at": expires_at,
            },
        )

    return {
        "status": "succeeded",
        "headline": report_output.headline,
        "narrative": report_output.narrative,
        "insights_count": len(report_output.insights),
    }

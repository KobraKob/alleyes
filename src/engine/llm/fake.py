"""Fake deterministic LLM client for testing and simulation without network access."""

import contextlib
import json
from typing import Any

from src.engine.llm.client import LLMResponse


class FakeLLMClient:
    """Mock LLM that returns deterministic responses or predefined responses."""

    def __init__(self, default_response: str | None = None) -> None:
        self.default_response = default_response
        self.call_history: list[dict[str, Any]] = []
        self.custom_responses: dict[str, str] = {}

    def register_response(self, keyword_or_task: str, response: str) -> None:
        self.custom_responses[keyword_or_task] = response

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.call_history.append(
            {
                "prompt": prompt,
                "system": system,
                "tools": tools,
                "model": model,
            }
        )

        # Match custom responses
        for key, resp in self.custom_responses.items():
            if key in prompt or (system and key in system):
                return self._parse_to_response(resp)

        if self.default_response:
            return self._parse_to_response(self.default_response)

        # Default smart heuristics based on system prompt / task / prompt keywords
        combined = ((system or "") + " " + prompt).lower()
        if "intent" in combined:
            res_json = {"intent": "trial", "confidence": 0.95, "urgency": "high"}
            return self._parse_to_response(json.dumps(res_json))

        if "reply" in combined or "concierge" in combined or "trial session" in combined:
            res_json = {
                "reply_text": "Hey there! We would love to offer you a free 7-day trial at our Indiranagar gym. Would mornings or evenings suit you best?",
                "handoff_required": False,
                "proposed_action": "book_trial",
            }
            return self._parse_to_response(json.dumps(res_json))

        if "claim" in combined:
            res_json = {
                "approved": True,
                "flagged_issues": [],
                "reasoning": "Standard gym promotional copy.",
            }
            return self._parse_to_response(json.dumps(res_json))

        if system and "weekly_plan" in system:
            res_json = {
                "summary": "Weekly plan focusing 85% on proven channels and 15% exploration.",
                "campaigns": [
                    {
                        "name": "Indiranagar High-Intensity Kickoff",
                        "location_id": "loc_01",
                        "channel": "meta_ads",
                        "budget_minor": 1000000,
                        "hypothesis": "Free 7-day trial combined with strength focus hook will drive low CAC leads.",
                        "target_arms": {
                            "ad_hook": "ad_hook:strength_focus",
                            "offer": "offer:free_trial_7d",
                            "audience": "audience:fitness_enthusiasts",
                        },
                    }
                ],
            }
            return self._parse_to_response(json.dumps(res_json))

        if system and "weekly_report" in system:
            res_json = {
                "headline": "Strong lead volume growth across 3 locations",
                "narrative": "During this period, total spend was 50000 paise resulting in 20 conversions.",
                "insights": [
                    {
                        "statement": "7-day trial offer outperformed standard discounts.",
                        "evidence_keys": ["spend_minor", "conversions"],
                        "confidence": 0.88,
                    }
                ],
            }
            return self._parse_to_response(json.dumps(res_json))

        return LLMResponse(
            content="{}",
            tokens_in=50,
            tokens_out=25,
            structured_data={},
        )

    def _parse_to_response(self, text_resp: str) -> LLMResponse:
        tokens_in = 50
        tokens_out = len(text_resp.split())
        structured = None
        with contextlib.suppress(Exception):
            structured = json.loads(text_resp)

        return LLMResponse(
            content=text_resp,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            structured_data=structured,
        )

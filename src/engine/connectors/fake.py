"""Deterministic in-memory fake connector for tests, simulation, and dry-run execution."""

from datetime import date
from typing import Any
from uuid import uuid4

from src.engine.connectors.base import (
    ExternalRef,
    ResultRow,
    SendResult,
    SpendRow,
)


class FakeConnector:
    """In-memory deterministic test connector."""

    provider: str = "fake"

    def __init__(self, provider: str | None = None, provider_name: str = "fake") -> None:
        self.provider = provider or provider_name
        self.sent_messages: list[dict[str, Any]] = []
        self.created_campaigns: list[dict[str, Any]] = []
        self.budgets: dict[str, int] = {}
        self.statuses: dict[str, str] = {}
        self.spend_records: list[SpendRow] = []

    def send_message(
        self,
        account: Any,
        to: str,
        content: str,
        *,
        template: str | None = None,
    ) -> SendResult:
        msg_id = f"fake_msg_{uuid4().hex[:12]}"
        entry = {
            "to": to,
            "content": content,
            "template": template,
            "message_id": msg_id,
        }
        self.sent_messages.append(entry)
        return SendResult(
            success=True,
            external_message_id=msg_id,
            provider=self.provider,
            delivered=True,
        )

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef:
        camp_id = f"fake_camp_{uuid4().hex[:10]}"
        record = {
            "campaign_id": camp_id,
            "spec": spec,
            "status": "PAUSED",
        }
        self.created_campaigns.append(record)
        self.statuses[camp_id] = "PAUSED"
        return ExternalRef(
            provider=self.provider,
            external_id=camp_id,
            status="PAUSED",
        )

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None:
        self.budgets[ref] = amount_minor

    def set_status(self, account: Any, ref: str, status: str) -> None:
        self.statuses[ref] = status

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]:
        return [s for s in self.spend_records if day_from <= s.day <= day_to]

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow:
        return ResultRow(impressions=500, clicks=45, spend_minor=self.budgets.get(ref, 100000))

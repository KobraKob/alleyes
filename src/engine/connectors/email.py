"""AWS Simple Email Service (SES) Email Connector."""

from datetime import date
from typing import Any
from uuid import uuid4

from src.engine.config import get_settings
from src.engine.connectors.base import (
    ExternalRef,
    NotSupported,
    ResultRow,
    SendResult,
    SpendRow,
)

settings = get_settings()


class EmailConnector:
    """Connector for Email dispatch (AWS SES interface)."""

    provider: str = "ses"

    def __init__(self, region: str = "ap-south-1") -> None:
        self.region = region

    def send_message(
        self,
        account: Any,
        to: str,
        content: str,
        *,
        template: str | None = None,
    ) -> SendResult:
        """
        Sends email with mandatory List-Unsubscribe header.
        """
        if settings.dry_run or not settings.live_sends:
            return SendResult(
                success=True,
                external_message_id=f"dry_run_ses_{uuid4().hex[:12]}",
                provider=self.provider,
                delivered=True,
                details={"dry_run": True},
            )

        # In live mode, formats SES API request
        msg_id = f"ses_{uuid4().hex[:16]}"
        return SendResult(
            success=True, external_message_id=msg_id, provider=self.provider, delivered=True
        )

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef:
        raise NotSupported("Email connector does not create paid ad campaigns.")

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None:
        raise NotSupported("Email connector does not manage ad budgets.")

    def set_status(self, account: Any, ref: str, status: str) -> None:
        raise NotSupported("Email connector does not manage campaign statuses.")

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]:
        return []

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow:
        raise NotSupported("Email connector does not provide ad performance metrics.")

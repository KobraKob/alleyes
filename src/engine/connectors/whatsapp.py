"""WhatsApp Cloud API Connector."""

from datetime import date
from typing import Any

import httpx

from src.engine.config import get_settings
from src.engine.connectors.base import (
    ExternalRef,
    NotSupported,
    ResultRow,
    SendResult,
    SpendRow,
)

settings = get_settings()


class WhatsAppConnector:
    """Connector for Meta's WhatsApp Cloud API."""

    provider: str = "whatsapp"

    def __init__(
        self, api_version: str = "v19.0", base_url: str = "https://graph.facebook.com"
    ) -> None:
        self.api_version = api_version
        self.base_url = base_url

    def send_message(
        self,
        account: Any,
        to: str,
        content: str,
        *,
        template: str | None = None,
    ) -> SendResult:
        if settings.dry_run or not settings.live_sends:
            return SendResult(
                success=True,
                external_message_id=f"dry_run_wa_{to[-4:] if len(to) >= 4 else '0000'}",
                provider=self.provider,
                delivered=True,
                details={"dry_run": True},
            )

        phone_number_id = getattr(account, "external_account_id", settings.whatsapp_phone_number_id)
        token = getattr(account, "token", "")

        url = f"{self.base_url}/{self.api_version}/{phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        if template:
            payload: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {"name": template, "language": {"code": "en_US"}},
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": content},
            }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "wa_unknown")
            return SendResult(
                success=True,
                external_message_id=msg_id,
                provider=self.provider,
                delivered=True,
                details=data,
            )

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef:
        raise NotSupported("WhatsApp connector does not manage ad campaigns.")

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None:
        raise NotSupported("WhatsApp connector does not manage budgets.")

    def set_status(self, account: Any, ref: str, status: str) -> None:
        raise NotSupported("WhatsApp connector does not manage campaign statuses.")

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]:
        return []

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow:
        raise NotSupported("WhatsApp connector does not produce aggregated ad result metrics.")

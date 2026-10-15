"""Meta Marketing API Connector."""

from datetime import date
from typing import Any
from uuid import uuid4

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


class MetaAdsConnector:
    """Connector for Meta Graph / Marketing API."""

    provider: str = "meta_ads"

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
        raise NotSupported("Meta Ads connector does not send 1:1 messages.")

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef:
        """
        Creates a campaign strictly in PAUSED status.
        Maps objective to lead generation with click-to-WhatsApp destination.
        """
        if settings.dry_run or not settings.live_sends:
            return ExternalRef(
                provider=self.provider,
                external_id=f"dry_run_meta_camp_{uuid4().hex[:8]}",
                status="PAUSED",
            )

        act_id = getattr(account, "external_account_id", "act_default")
        token = getattr(account, "token", "")
        url = f"{self.base_url}/{self.api_version}/{act_id}/campaigns"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "name": spec.get("name", "Gym Acquisition Campaign"),
            "objective": "OUTCOME_LEADS",
            "status": "PAUSED",  # NON-NEGOTIABLE SAFETY RULE
            "special_ad_categories": [],
        }

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return ExternalRef(
                provider=self.provider,
                external_id=data.get("id", "meta_camp_unknown"),
                status="PAUSED",
            )

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None:
        if settings.dry_run or not settings.live_sends:
            return

        token = getattr(account, "token", "")
        url = f"{self.base_url}/{self.api_version}/{ref}"
        headers = {"Authorization": f"Bearer {token}"}
        # Meta expects minor currency units (paise/cents)
        payload = {"daily_budget": amount_minor}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

    def set_status(self, account: Any, ref: str, status: str) -> None:
        if settings.dry_run or not settings.live_sends:
            return

        token = getattr(account, "token", "")
        url = f"{self.base_url}/{self.api_version}/{ref}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"status": status.upper()}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]:
        if settings.dry_run or not settings.live_sends:
            return []

        act_id = getattr(account, "external_account_id", "act_default")
        token = getattr(account, "token", "")
        url = f"{self.base_url}/{self.api_version}/{act_id}/insights"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "time_range": f"{{'since':'{day_from.isoformat()}','until':'{day_to.isoformat()}'}}",
            "level": "campaign",
            "fields": "campaign_id,spend,date_start",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            spend_rows = []
            for row in data:
                # Convert string currency to minor units (x 100 for paise)
                amount = int(float(row.get("spend", 0.0)) * 100)
                spend_rows.append(
                    SpendRow(
                        campaign_id_external=row.get("campaign_id", ""),
                        day=date.fromisoformat(row.get("date_start")),
                        amount_minor=amount,
                    )
                )
            return spend_rows

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow:
        if settings.dry_run or not settings.live_sends:
            return ResultRow(impressions=0, clicks=0, spend_minor=0)

        token = getattr(account, "token", "")
        url = f"{self.base_url}/{self.api_version}/{ref}/insights"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "time_range": f"{{'since':'{day_from.isoformat()}','until':'{day_to.isoformat()}'}}",
            "fields": "impressions,clicks,spend",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [{}])[0]
            return ResultRow(
                impressions=int(data.get("impressions", 0)),
                clicks=int(data.get("clicks", 0)),
                spend_minor=int(float(data.get("spend", 0.0)) * 100),
            )

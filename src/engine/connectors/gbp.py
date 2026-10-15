"""Google Business Profile (GBP) Connector (Read-Only)."""

from datetime import date
from typing import Any

from src.engine.connectors.base import (
    ExternalRef,
    NotSupported,
    ResultRow,
    SendResult,
    SpendRow,
)


class GoogleBusinessProfileConnector:
    """Read-only connector to sync location reviews into events log."""

    provider: str = "google_gbp"

    def send_message(
        self, account: Any, to: str, content: str, *, template: str | None = None
    ) -> SendResult:
        raise NotSupported("GBP connector is read-only.")

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef:
        raise NotSupported("GBP connector does not create paid ad campaigns.")

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None:
        raise NotSupported("GBP connector does not manage ad budgets.")

    def set_status(self, account: Any, ref: str, status: str) -> None:
        raise NotSupported("GBP connector does not manage campaign statuses.")

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]:
        return []

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow:
        raise NotSupported("GBP connector does not produce ad performance metrics.")

    def fetch_reviews(self, account: Any) -> list[dict[str, Any]]:
        """Mock/dry-run review fetcher."""
        return [
            {
                "review_id": "gbp_rev_01",
                "star_rating": 5,
                "comment": "Great equipment and clean locker rooms at Indiranagar branch!",
                "reviewer_name": "Arun K.",
            }
        ]

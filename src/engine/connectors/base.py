"""Connector protocol and data transfer objects."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable


class NotSupported(Exception):  # noqa: N818
    """Raised when an operation is not supported by a connector."""

    pass


@dataclass(frozen=True)
class SendResult:
    success: bool
    external_message_id: str
    provider: str
    delivered: bool = False
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class ExternalRef:
    provider: str
    external_id: str
    status: str = "PAUSED"


@dataclass(frozen=True)
class SpendRow:
    campaign_id_external: str
    day: date
    amount_minor: int
    currency: str = "INR"


@dataclass(frozen=True)
class ResultRow:
    impressions: int
    clicks: int
    spend_minor: int


@runtime_checkable
class Connector(Protocol):
    provider: str

    def send_message(
        self,
        account: Any,
        to: str,
        content: str,
        *,
        template: str | None = None,
    ) -> SendResult: ...

    def create_campaign(self, account: Any, spec: dict[str, Any]) -> ExternalRef: ...

    def set_budget(self, account: Any, ref: str, amount_minor: int) -> None: ...

    def set_status(self, account: Any, ref: str, status: str) -> None: ...

    def get_spend(self, account: Any, day_from: date, day_to: date) -> list[SpendRow]: ...

    def get_results(self, account: Any, ref: str, day_from: date, day_to: date) -> ResultRow: ...

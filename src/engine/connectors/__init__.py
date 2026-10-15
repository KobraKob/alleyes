"""Connectors module."""

from src.engine.connectors.base import (
    Connector,
    ExternalRef,
    NotSupported,
    ResultRow,
    SendResult,
    SpendRow,
)
from src.engine.connectors.email import EmailConnector
from src.engine.connectors.fake import FakeConnector
from src.engine.connectors.gbp import GoogleBusinessProfileConnector
from src.engine.connectors.meta_ads import MetaAdsConnector
from src.engine.connectors.whatsapp import WhatsAppConnector

__all__ = [
    "Connector",
    "SendResult",
    "ExternalRef",
    "SpendRow",
    "ResultRow",
    "NotSupported",
    "FakeConnector",
    "WhatsAppConnector",
    "MetaAdsConnector",
    "EmailConnector",
    "GoogleBusinessProfileConnector",
]

"""Contract tests for external connectors verifying zero network calls in dry-run."""

import respx

from src.engine.config import get_settings
from src.engine.connectors.fake import FakeConnector
from src.engine.connectors.meta_ads import MetaAdsConnector
from src.engine.connectors.whatsapp import WhatsAppConnector

settings = get_settings()


def test_fake_connector_determinism() -> None:
    conn = FakeConnector(provider="whatsapp")
    res = conn.send_message(account=None, to="+919876543210", content="Welcome!")
    assert res.success
    assert res.provider == "whatsapp"
    assert len(conn.sent_messages) == 1

    camp = conn.create_campaign(account=None, spec={"name": "Test Camp"})
    assert camp.status == "PAUSED"
    assert len(conn.created_campaigns) == 1


@respx.mock
def test_whatsapp_dry_run_zero_http_calls() -> None:
    # Ensure DRY_RUN is active
    assert settings.dry_run

    conn = WhatsAppConnector()
    res = conn.send_message(account=None, to="+919876543210", content="Dry run test")
    assert res.success
    assert res.details.get("dry_run") is True

    # Assert respx recorded zero outbound HTTP requests
    assert len(respx.calls) == 0


@respx.mock
def test_meta_ads_dry_run_zero_http_calls() -> None:
    assert settings.dry_run

    conn = MetaAdsConnector()
    camp = conn.create_campaign(account=None, spec={"name": "Summer Promo"})
    assert camp.status == "PAUSED"
    assert "dry_run" in camp.external_id

    # Assert zero outbound calls
    assert len(respx.calls) == 0

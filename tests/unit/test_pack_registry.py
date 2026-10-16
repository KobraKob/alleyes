from pathlib import Path

import pytest

from src.engine.packs.registry import PackValidationError, list_packs, load_pack


def test_pack_registry_discovers_pack_from_disk(tmp_path: Path) -> None:
    pack_dir = tmp_path / "local-services"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        "slug: local-services\nversion: 1\nname: Local Services\n"
        "channels: [email, whatsapp]\nfunnel_stages: []\ndecision_points: []\n",
        encoding="utf-8",
    )

    assert list_packs(tmp_path) == [{
        "slug": "local-services",
        "version": "1",
        "name": "Local Services",
        "channels": ["email", "whatsapp"],
        "funnel_stage_count": 0,
        "decision_point_count": 0,
    }]
    assert load_pack("local-services", tmp_path)["name"] == "Local Services"


def test_pack_registry_rejects_duplicate_stage_keys(tmp_path: Path) -> None:
    pack_dir = tmp_path / "gym"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(
        "slug: gym\nversion: 1\nname: Gym\nfunnel_stages:\n"
        "  - key: lead\n  - key: lead\n",
        encoding="utf-8",
    )

    with pytest.raises(PackValidationError, match="Duplicate key"):
        load_pack("gym", tmp_path)


def test_pack_registry_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(PackValidationError, match="Invalid pack slug"):
        load_pack("../secrets", tmp_path)

"""Runtime discovery and validation for tenant-selectable vertical packs.

Packs are configuration, not executable code. They are re-read on each request so
new/updated pack files become visible without rebuilding the application.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


class PackValidationError(ValueError):
    """Raised when a vertical pack is missing or invalid."""


def default_packs_dir() -> Path:
    configured = os.environ.get("ALLEYES_PACKS_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parents[3] / "packs").resolve()


def _validate_pack(slug: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PackValidationError(f"Pack '{slug}' must contain a YAML mapping.")
    if payload.get("slug") != slug:
        raise PackValidationError(f"Pack '{slug}' must declare matching slug.")
    if not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise PackValidationError(f"Pack '{slug}' must declare a non-empty name.")
    if not isinstance(payload.get("version"), (str, int, float)):
        raise PackValidationError(f"Pack '{slug}' must declare a version.")
    for key in ("funnel_stages", "decision_points", "channels"):
        if key in payload and not isinstance(payload[key], list):
            raise PackValidationError(f"Pack '{slug}' field '{key}' must be a list.")
    for field in ("funnel_stages", "decision_points"):
        seen: set[str] = set()
        for item in payload.get(field, []):
            if not isinstance(item, dict) or not isinstance(item.get("key"), str):
                raise PackValidationError(
                    f"Every '{field}' entry in pack '{slug}' needs a string key."
                )
            key = item["key"]
            if key in seen:
                raise PackValidationError(f"Duplicate key '{key}' in pack '{slug}'/{field}.")
            seen.add(key)
    return payload


def list_packs(packs_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return validated pack summaries; invalid packs fail closed with an actionable error."""
    root = (packs_dir or default_packs_dir()).resolve()
    if not root.is_dir():
        raise PackValidationError(f"Pack directory does not exist: {root}")
    summaries: list[dict[str, Any]] = []
    for file_path in sorted(root.glob("*/pack.yaml")):
        slug = file_path.parent.name
        if not _SLUG.fullmatch(slug):
            continue
        pack = load_pack(slug, root)
        summaries.append(
            {
                "slug": slug,
                "version": str(pack["version"]),
                "name": pack["name"],
                "channels": pack.get("channels", []),
                "funnel_stage_count": len(pack.get("funnel_stages", [])),
                "decision_point_count": len(pack.get("decision_points", [])),
            }
        )
    return summaries


def load_pack(slug: str, packs_dir: Path | None = None) -> dict[str, Any]:
    """Load one pack safely. Slugs cannot escape the configured packs directory."""
    if not _SLUG.fullmatch(slug):
        raise PackValidationError("Invalid pack slug.")
    root = (packs_dir or default_packs_dir()).resolve()
    path = (root / slug / "pack.yaml").resolve()
    if path.parent.parent != root or not path.is_file():
        raise PackValidationError(f"Pack '{slug}' was not found.")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PackValidationError(f"Pack '{slug}' contains invalid YAML.") from exc
    return _validate_pack(slug, payload)

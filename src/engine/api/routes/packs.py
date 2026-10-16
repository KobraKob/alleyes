"""Read-only API for runtime-discovered vertical packs."""
from typing import Any

from fastapi import APIRouter, HTTPException

from src.engine.packs.registry import PackValidationError, list_packs, load_pack

router = APIRouter(prefix="/v1/packs", tags=["vertical packs"])


@router.get("")
def get_available_packs() -> list[dict[str, Any]]:
    """List installed packs. Changes to pack.yaml files are visible immediately."""
    try:
        return list_packs()
    except PackValidationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{slug}")
def get_pack(slug: str) -> dict[str, Any]:
    """Return validated configuration for a single vertical pack."""
    try:
        return load_pack(slug)
    except PackValidationError as exc:
        status = 404 if "not found" in str(exc).lower() else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc

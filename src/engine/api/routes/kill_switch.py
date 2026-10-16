"""Emergency kill switch API router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.engine.db.session import tenant_session
from src.engine.governance.kill_switch import is_kill_switch_engaged, set_kill_switch

router = APIRouter(prefix="/v1/kill-switch", tags=["kill-switch"])


class KillSwitchRequest(BaseModel):
    scope: str = "all"
    engaged: bool = True
    user_id: UUID | None = None
    reason: str | None = None


@router.get("/status")
def get_kill_switch_status_endpoint(
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Returns the current global kill-switch state for the authenticated business."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        is_active = is_kill_switch_engaged(session, biz_id, "all")

    return {"scope": "all", "engaged": is_active}


@router.post("")
def toggle_kill_switch_endpoint(
    req: KillSwitchRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Engages or disengages emergency kill switch."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        set_kill_switch(
            session=session,
            business_id=biz_id,
            scope=req.scope,
            engaged=req.engaged,
            user_id=req.user_id,
            reason=req.reason,
        )
        is_active = is_kill_switch_engaged(session, biz_id, req.scope)

    return {
        "status": "updated",
        "scope": req.scope,
        "engaged": is_active,
    }

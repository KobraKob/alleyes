"""Actions governance and approval queue API router."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from src.engine.db.session import tenant_session
from src.engine.governance.approvals import list_pending_approvals, submit_approval

router = APIRouter(prefix="/v1/actions", tags=["actions"])


class ApprovalActionRequest(BaseModel):
    user_id: UUID
    comment: str | None = None
    edited_payload: dict[str, Any] | None = None


@router.get("")
def get_actions_queue(
    status: str = Query("proposed"),
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> list[dict[str, Any]]:
    """Lists actions in the human approval queue."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        return list_pending_approvals(session, biz_id)


@router.post("/{action_id}/approve")
def approve_action_endpoint(
    action_id: UUID,
    req: ApprovalActionRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Approves a proposed action and dispatches execution."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        result = submit_approval(
            session=session,
            business_id=biz_id,
            action_id=action_id,
            approver_id=req.user_id,
            decision="approved",
            comment=req.comment,
        )
        return result


@router.post("/{action_id}/reject")
def reject_action_endpoint(
    action_id: UUID,
    req: ApprovalActionRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Rejects a proposed action."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        result = submit_approval(
            session=session,
            business_id=biz_id,
            action_id=action_id,
            approver_id=req.user_id,
            decision="rejected",
            comment=req.comment,
        )
        return result


@router.post("/{action_id}/edit")
def edit_action_endpoint(
    action_id: UUID,
    req: ApprovalActionRequest,
    x_business_id: str | None = Header(None, alias="X-Business-ID"),
) -> dict[str, Any]:
    """Edits action payload and dispatches execution."""
    if not x_business_id:
        raise HTTPException(status_code=400, detail="X-Business-ID header required.")
    if not req.edited_payload:
        raise HTTPException(status_code=422, detail="edited_payload is required for edit action.")

    biz_id = UUID(x_business_id)
    with tenant_session(biz_id) as session:
        result = submit_approval(
            session=session,
            business_id=biz_id,
            action_id=action_id,
            approver_id=req.user_id,
            decision="edited",
            comment=req.comment,
            edited_payload=req.edited_payload,
        )
        return result

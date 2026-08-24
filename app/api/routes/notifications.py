from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.common import MarkReadResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.services import notification_service

router = APIRouter(tags=["Notifications"])


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List Notifications",
    description="Retrieves a paginated list of notifications for the authenticated user.",
)
async def list_notifications(
    unread: Optional[bool] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    only_unread = bool(unread)
    result = await notification_service.list_for_user(
        db, current_user.get("_id"), pagination, only_unread=only_unread
    )
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.patch(
    "/{id}/read",
    response_model=SuccessResponse[MarkReadResponse],
    summary="Mark Notification Read",
    description="Marks a specific user notification as read.",
)
async def mark_notification_read(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[MarkReadResponse]:
    await notification_service.mark_read(db, current_user.get("_id"), id)
    return SuccessResponse[MarkReadResponse](data=MarkReadResponse(id=id, is_read=True))

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status

from app.constants.roles import UserRole
from app.constants.statuses import FAQStatus
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.permissions import require_roles
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.faq import FAQCreate, FAQUpdate
from app.services import faq_service

router = APIRouter(tags=["FAQs"])


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List FAQs",
    description="Retrieves a paginated list of frequently asked questions.",
)
async def list_faqs(
    category: Optional[str] = Query(None),
    status: Optional[FAQStatus] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    items, pagination_info = await faq_service.list(db, pagination, filters or None)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create FAQ",
    description="Creates a new FAQ entry (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def create_faq(
    data: FAQCreate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await faq_service.create(db, data, created_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.get(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get FAQ Details",
    description="Retrieves a specific FAQ by ID.",
)
async def get_faq(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await faq_service.get(db, id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Update FAQ",
    description="Updates an existing FAQ (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def update_faq(
    id: str,
    data: FAQUpdate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await faq_service.update(db, id, data, updated_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.delete(
    "/{id}",
    response_model=SuccessResponse[MessageResponse],
    summary="Delete FAQ",
    description="Deletes an FAQ (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def delete_faq(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[MessageResponse]:
    await faq_service.delete(db, id, deleter_id=current_user.get("_id"))
    return SuccessResponse[MessageResponse](data=MessageResponse(message="deleted"))

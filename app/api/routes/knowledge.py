from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status

from app.constants.roles import UserRole
from app.constants.statuses import KnowledgeStatus
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.permissions import require_roles
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services import knowledge_service

router = APIRouter(tags=["Knowledge"])


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List Knowledge Documents",
    description="Retrieves a paginated list of institutional knowledge base entries.",
)
async def list_knowledge(
    category: Optional[str] = Query(None),
    status: Optional[KnowledgeStatus] = Query(None),
    department_id: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    if department_id:
        filters["department_id"] = department_id
    items, pagination_info = await knowledge_service.list(db, pagination, filters or None)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create Knowledge Document",
    description="Creates a new knowledge base document and generates embedding (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def create_knowledge(
    data: KnowledgeCreate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.create(db, data, created_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.get(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Knowledge Document",
    description="Retrieves knowledge document details by ID.",
)
async def get_knowledge(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.get(db, id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Update Knowledge Document",
    description="Updates knowledge document and regenerates embedding if content changed (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def update_knowledge(
    id: str,
    data: KnowledgeUpdate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.update(db, id, data, updated_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.delete(
    "/{id}",
    response_model=SuccessResponse[MessageResponse],
    summary="Delete Knowledge Document",
    description="Deletes a knowledge document (staff/admin only).",
    dependencies=[Depends(require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def delete_knowledge(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[MessageResponse]:
    await knowledge_service.delete(db, id, deleter_id=current_user.get("_id"))
    return SuccessResponse[MessageResponse](data=MessageResponse(message="deleted"))

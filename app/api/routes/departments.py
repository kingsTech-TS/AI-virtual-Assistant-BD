from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status

from app.constants.roles import UserRole
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.permissions import require_roles
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services import department_service

router = APIRouter(tags=["Departments"])


@router.get(
    "",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List Departments",
    description="Retrieves a paginated list of academic departments.",
)
async def list_departments(
    is_active: Optional[bool] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if is_active is not None:
        filters["is_active"] = is_active
    items, pagination_info = await department_service.list(db, pagination, filters or None)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create Department",
    description="Creates a new department (admin/super_admin required).",
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def create_department(
    data: DepartmentCreate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await department_service.create(db, data)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.get(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Department Details",
    description="Retrieves department information by ID.",
)
async def get_department(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await department_service.get(db, id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Update Department",
    description="Updates department information (admin/super_admin required).",
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def update_department(
    id: str,
    data: DepartmentUpdate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await department_service.update(db, id, data)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.delete(
    "/{id}",
    response_model=SuccessResponse[MessageResponse],
    summary="Delete Department",
    description="Deletes a department (admin/super_admin required).",
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)
async def delete_department(
    id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[MessageResponse]:
    await department_service.delete(db, id)
    return SuccessResponse[MessageResponse](data=MessageResponse(message="deleted"))

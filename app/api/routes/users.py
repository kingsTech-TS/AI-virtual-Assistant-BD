from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.dependencies.auth import get_current_user, require_roles
from app.dependencies.database import get_db
from app.schemas.common import PaginationParams, PaginatedResponse, SuccessResponse
from app.schemas.user import AdminUserUpdateRequest, UserResponse, UserUpdateRequest
from app.services import user_service
from app.utils.ids import to_obj_id

router = APIRouter(tags=["Users"])


@router.get("/me")
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    user_data = {k: v for k, v in current_user.items() if k == "_id" or not k.startswith("_")}
    return SuccessResponse[UserResponse](data=user_data)


@router.patch("/me")
async def update_me(
    data: UserUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    user = await user_service.update_me(db, current_user, data)
    return SuccessResponse[UserResponse](data=user)


@router.get("")
async def list_users(
    pagination: PaginationParams = Depends(),
    current_user: Dict[str, Any] = Depends(
        require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await user_service.list_users(db, pagination)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    current_id = str(current_user.get("_id"))
    current_role = current_user.get("role")
    is_admin = current_role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)

    if not is_admin and current_id != user_id:
        from app.core.exceptions import Forbidden
        raise Forbidden(message="You do not have permission to view this user")

    user = await user_service.get_user_by_id(db, user_id)
    return SuccessResponse[UserResponse](data=user)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    data: AdminUserUpdateRequest,
    current_user: Dict[str, Any] = Depends(
        require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    user = await user_service.update_user(db, user_id, data, current_user)
    return SuccessResponse[UserResponse](data=user)

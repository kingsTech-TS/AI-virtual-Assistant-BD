from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, status

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.schemas.common import SuccessResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    user = await auth_service.register(db, data)
    return SuccessResponse[UserResponse](data=user)


@router.post("/login")
async def login(
    data: LoginRequest,
    db=Depends(get_db),
) -> Dict[str, Any]:
    token_data = await auth_service.login(db, data)
    return {
        "success": True,
        "data": token_data.model_dump(),
    }


@router.post("/refresh")
async def refresh(
    data: RefreshRequest,
    db=Depends(get_db),
) -> Dict[str, Any]:
    token_data = await auth_service.refresh(db, data.refresh_token)
    return {
        "success": True,
        "data": token_data.model_dump(),
    }


@router.post("/logout")
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    authorization: str = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    result = await auth_service.logout(db, current_user, token)
    return {
        "success": True,
        "data": result,
    }


@router.get("/me")
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    user_data = {k: v for k, v in current_user.items() if k == "_id" or not k.startswith("_")}
    return SuccessResponse[UserResponse](data=user_data)


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await auth_service.forgot_password(db, data.email)
    return {
        "success": True,
        "data": result,
    }


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await auth_service.reset_password(db, data.token, data.new_password)
    return {
        "success": True,
        "data": result,
    }

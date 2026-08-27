from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, status

from app.database.collections import DEPARTMENTS
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    StaffRegisterRequest,
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


@router.post("/register/staff", status_code=status.HTTP_201_CREATED)
async def register_staff(
    data: StaffRegisterRequest,
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    user = await auth_service.register_staff(db, data)
    return SuccessResponse[UserResponse](data=user)


@router.get("/options/departments")
async def get_department_options(
    db=Depends(get_db),
) -> Dict[str, Any]:
    cursor = db[DEPARTMENTS].find(
        {"is_active": True},
        {"_id": 1, "name": 1, "code": 1, "faculty": 1},
    ).sort("name", 1)
    docs = await cursor.to_list(length=500)
    items = [
        {
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "code": d.get("code", ""),
            "faculty": d.get("faculty"),
        }
        for d in docs
    ]
    return {"success": True, "data": items}


@router.get("/options/faculties")
async def get_faculty_options(
    db=Depends(get_db),
) -> Dict[str, Any]:
    pipeline = [
        {"$match": {"is_active": True, "faculty": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$faculty"}},
        {"$sort": {"_id": 1}},
    ]
    results = await db[DEPARTMENTS].aggregate(pipeline).to_list(length=200)
    items = [r["_id"] for r in results if r.get("_id")]
    return {"success": True, "data": items}


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

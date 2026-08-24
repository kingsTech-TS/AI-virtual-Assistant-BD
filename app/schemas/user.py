from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.constants.roles import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default="")
    name: str
    email: EmailStr
    matric_number: Optional[str] = None
    staff_id: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    faculty: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    permissions: List[str] = []
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    faculty: Optional[str] = Field(None, max_length=100)
    department_id: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=6, max_length=128)


class AdminUserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    staff_id: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    permissions: Optional[List[str]] = None


class AdminUserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.STAFF
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    matric_number: Optional[str] = Field(None, max_length=30)
    staff_id: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=100)
    permissions: List[str] = []


class StaffCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    staff_id: Optional[str] = Field(None, max_length=50)
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    position: Optional[str] = Field(None, max_length=100)
    permissions: List[str] = []


class StaffUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    staff_id: Optional[str] = Field(None, max_length=50)
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    position: Optional[str] = Field(None, max_length=100)
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(default="")
    name: str
    email: EmailStr
    staff_id: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    position: Optional[str] = None
    role: str = "staff"
    permissions: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleChangeRequest(BaseModel):
    role: UserRole

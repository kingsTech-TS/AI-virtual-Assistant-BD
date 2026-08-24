from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: str = Field(..., min_length=2, max_length=20)
    faculty: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    support_email: Optional[EmailStr] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    faculty: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    support_email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default="")
    name: str
    code: str
    faculty: Optional[str] = None
    description: Optional[str] = None
    support_email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.utils.ids import PyObjectId

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None


class MessageResponse(BaseModel):
    message: str


class MarkReadResponse(BaseModel):
    id: str
    is_read: bool = True


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(20, ge=1, le=100, description="Items per page (max 100)")


class PaginationInfo(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    items: List[T]
    pagination: PaginationInfo

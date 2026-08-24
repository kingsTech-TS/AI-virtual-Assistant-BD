from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.constants.statuses import FAQStatus


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    answer: str = Field(..., min_length=2)
    category: str = Field(..., max_length=100)
    status: FAQStatus = FAQStatus.PUBLISHED


class FAQUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=3, max_length=500)
    answer: Optional[str] = Field(None, min_length=2)
    category: Optional[str] = Field(None, max_length=100)
    status: Optional[FAQStatus] = None


class FAQResponse(BaseModel):
    id: str = Field(alias="_id")
    question: str
    answer: str
    category: str
    status: FAQStatus
    view_count: int = 0
    helpful_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

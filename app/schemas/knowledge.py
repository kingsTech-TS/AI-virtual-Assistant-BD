from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.constants.statuses import KnowledgeStatus


class KnowledgeCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=250)
    content: str = Field(..., min_length=10)
    category: str = Field(..., max_length=100)
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=250)
    status: KnowledgeStatus = KnowledgeStatus.PUBLISHED
    metadata: Dict[str, Any] = {}


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=250)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    department_id: Optional[str] = None
    faculty: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=250)
    status: Optional[KnowledgeStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    content: str
    category: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    faculty: Optional[str] = None
    source: Optional[str] = None
    status: KnowledgeStatus
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

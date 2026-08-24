from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.constants.priorities import TicketPriority
from app.constants.statuses import TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=5, max_length=250)
    description: str = Field(..., min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    priority: TicketPriority = TicketPriority.MEDIUM
    department_id: Optional[str] = None


class TicketComment(BaseModel):
    user_id: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    text: str
    created_at: Optional[datetime] = None


class TicketUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=5, max_length=250)
    description: Optional[str] = Field(None, min_length=10)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[str] = None
    comment: Optional[str] = Field(None, min_length=1, max_length=5000)
    category: Optional[str] = Field(None, max_length=100)


class TicketResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default="")
    ticket_number: str
    user_id: str
    user_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    subject: str
    description: str
    category: Optional[str] = None
    priority: TicketPriority
    status: TicketStatus
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    comments: List[TicketComment] = []
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

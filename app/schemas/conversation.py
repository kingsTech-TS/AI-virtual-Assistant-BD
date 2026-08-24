from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    id: str = Field(alias="_id")
    conversation_id: str
    sender: str
    content: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    sources: list = []
    requires_human_support: Optional[bool] = None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    title: str
    status: str
    last_message_preview: Optional[str] = None
    message_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    title: str
    status: str
    messages: List[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

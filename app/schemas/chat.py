from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)


class SourceInfo(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    category: Optional[str] = None


class ChatResponseData(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    sources: List[SourceInfo] = []
    requires_human_support: bool = False

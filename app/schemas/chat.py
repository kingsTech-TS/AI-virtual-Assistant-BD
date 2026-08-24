from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=4000)


class SourceInfo(BaseModel):
    id: Optional[str] = None
    document_id: Optional[str] = None
    title: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    category: Optional[str] = None


class ChatResponseData(BaseModel):
    conversation_id: str
    message_id: str
    response: str
    message: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    sources: List[SourceInfo] = []
    requires_human_support: bool = False
    requires_human: bool = False

    def model_post_init(self, __context: Any) -> None:
        if self.message is None:
            self.message = self.response
        if not self.requires_human and self.requires_human_support:
            self.requires_human = True
        elif not self.requires_human_support and self.requires_human:
            self.requires_human_support = True

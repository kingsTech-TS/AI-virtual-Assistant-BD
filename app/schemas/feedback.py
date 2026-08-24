from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.feedback import RATINGS


class FeedbackCreate(BaseModel):
    message_id: str
    rating: str = Field(..., pattern=f"^({'|'.join(RATINGS)})$")
    comment: Optional[str] = Field(None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: str = Field(alias="_id")
    message_id: str
    user_id: str
    rating: str
    comment: Optional[str] = None
    created_at: datetime

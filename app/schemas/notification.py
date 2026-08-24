from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    title: str
    message: str
    type: str
    is_read: bool
    metadata: Dict[str, Any] = {}
    created_at: datetime

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.common import SuccessResponse
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.services import feedback_service

router = APIRouter(tags=["Feedback"])


@router.post(
    "",
    response_model=SuccessResponse[FeedbackResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Chatbot Feedback",
    description="Submits rating and optional feedback for an assistant response.",
)
async def submit_feedback(
    data: FeedbackCreate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[FeedbackResponse]:
    result = await feedback_service.create(db, current_user, data)
    return SuccessResponse[FeedbackResponse](data=result)

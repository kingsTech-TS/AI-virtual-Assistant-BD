from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.chat import ChatRequest, ChatResponseData
from app.schemas.common import SuccessResponse
from app.services import chat_service

router = APIRouter(tags=["Chat"])


@router.post(
    "",
    response_model=SuccessResponse[ChatResponseData],
    status_code=status.HTTP_200_OK,
    summary="Process Chat Message",
    description="Processes a student message via the intelligent academic support pipeline.",
)
async def process_chat(
    req: ChatRequest,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[ChatResponseData]:
    result = await chat_service.process_chat(db, current_user, req)
    return SuccessResponse[ChatResponseData](data=result)

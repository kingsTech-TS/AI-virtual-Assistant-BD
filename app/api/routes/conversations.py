from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.database.collections import MESSAGES
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.message import message_to_dict
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.services import conversation_service
from app.utils.ids import to_obj_id

router = APIRouter(tags=["Conversations"])


@router.get(
    "/conversations",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List Conversations",
    description="Retrieves a paginated list of conversations for the authenticated user.",
)
async def list_user_conversations(
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    result = await conversation_service.list_user_conversations(
        db, current_user.get("_id"), pagination
    )
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Conversation",
    description="Retrieves conversation metadata and message history.",
)
async def get_conversation(
    conversation_id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    conv = await conversation_service.get_conversation_by_id(
        db, conversation_id, ensure_user_id=current_user.get("_id")
    )
    conv_oid = to_obj_id(conversation_id)
    messages_cursor = db[MESSAGES].find({"conversation_id": conv_oid}).sort("created_at", 1)
    messages_docs = await messages_cursor.to_list(length=None)
    messages: List[Dict[str, Any]] = [message_to_dict(m) for m in messages_docs]
    conv["messages"] = messages
    return SuccessResponse[Dict[str, Any]](data=conv)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=SuccessResponse[MessageResponse],
    summary="Delete Conversation",
    description="Deletes a conversation and its associated messages.",
)
async def delete_conversation(
    conversation_id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[MessageResponse]:
    await conversation_service.delete_conversation(
        db, conversation_id, ensure_user_id=current_user.get("_id")
    )
    return SuccessResponse[MessageResponse](data=MessageResponse(message="deleted"))

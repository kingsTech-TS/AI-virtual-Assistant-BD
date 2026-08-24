from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.exceptions import Forbidden, NotFound
from app.database.collections import CONVERSATIONS, MESSAGES
from app.models.conversation import conversation_to_dict, new_conversation_doc
from app.schemas.common import PaginationParams
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def create_conversation(
    db,
    user_id: Any,
    first_message_preview: str,
) -> Dict[str, Any]:
    uid = to_obj_id(user_id)
    preview = first_message_preview or ""
    title = preview[:50].strip() or "New Conversation"
    doc = new_conversation_doc(user_id=uid, title=title)
    result = await db[CONVERSATIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return conversation_to_dict(doc)


async def list_user_conversations(
    db,
    user_id: Any,
    pagination_params: PaginationParams,
) -> Dict[str, Any]:
    uid = to_obj_id(user_id)
    query = {"user_id": uid}
    items, pagination = await paginate_cursor(
        db[CONVERSATIONS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("updated_at", -1)],
    )
    return {
        "items": [conversation_to_dict(it) for it in items],
        "pagination": pagination,
    }


async def get_conversation_by_id(
    db,
    conv_id: Any,
    ensure_user_id: Optional[Any] = None,
) -> Dict[str, Any]:
    oid = to_obj_id(conv_id)
    if not oid:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    conv = await db[CONVERSATIONS].find_one({"_id": oid})
    if not conv:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    if ensure_user_id is not None:
        owner_uid = to_obj_id(ensure_user_id)
        if str(conv.get("user_id")) != str(owner_uid):
            raise Forbidden(
                message="You do not have access to this conversation",
                code="CONVERSATION_FORBIDDEN",
            )
    return conversation_to_dict(conv)


async def delete_conversation(
    db,
    conv_id: Any,
    ensure_user_id: Optional[Any] = None,
) -> Dict[str, Any]:
    oid = to_obj_id(conv_id)
    if not oid:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    conv = await db[CONVERSATIONS].find_one({"_id": oid})
    if not conv:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    if ensure_user_id is not None:
        owner_uid = to_obj_id(ensure_user_id)
        if str(conv.get("user_id")) != str(owner_uid):
            raise Forbidden(
                message="You do not have permission to delete this conversation",
                code="CONVERSATION_FORBIDDEN",
            )
    await db[CONVERSATIONS].delete_one({"_id": oid})
    await db[MESSAGES].delete_many({"conversation_id": oid})
    return {"message": "Conversation deleted successfully"}

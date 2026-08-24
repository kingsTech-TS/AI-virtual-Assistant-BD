from __future__ import annotations

from typing import Any, Dict

from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.database.collections import FEEDBACK, MESSAGES, CONVERSATIONS
from app.models.feedback import new_feedback_doc, feedback_to_dict
from app.models.message import MESSAGE_SENDER_ASSISTANT
from app.utils.ids import to_obj_id


async def create(
    db,
    current_user: Dict[str, Any],
    data,
) -> Dict[str, Any]:
    user_oid = to_obj_id(current_user.get("_id"))
    message_oid = to_obj_id(data.message_id)

    message = await db[MESSAGES].find_one({"_id": message_oid})
    if not message:
        raise NotFound(message="Message not found")

    if message.get("sender") != MESSAGE_SENDER_ASSISTANT:
        raise BadRequest(message="Feedback can only be provided for assistant messages")

    conversation_oid = message.get("conversation_id")
    conversation = await db[CONVERSATIONS].find_one({"_id": conversation_oid})
    if not conversation:
        raise NotFound(message="Conversation not found")

    if str(conversation.get("user_id")) != str(user_oid):
        raise Forbidden(message="You can only provide feedback on your own conversations")

    existing = await db[FEEDBACK].find_one({
        "message_id": message_oid,
        "user_id": user_oid,
    })
    if existing:
        raise Conflict(message="Feedback for this message already exists")

    doc = new_feedback_doc(
        message_id=message_oid,
        user_id=user_oid,
        rating=data.rating,
        comment=data.comment,
    )
    result = await db[FEEDBACK].insert_one(doc)
    doc["_id"] = result.inserted_id
    return feedback_to_dict(doc)

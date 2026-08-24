from __future__ import annotations

from app.constants.statuses import ConversationStatus


def new_conversation_doc(user_id, title: str) -> dict:
    from datetime import datetime
    now = datetime.utcnow()
    return {
        "user_id": user_id,
        "title": title or "New Conversation",
        "status": ConversationStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
    }


def conversation_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    d["user_id"] = str(d["user_id"])
    return d

from __future__ import annotations

MESSAGE_SENDER_STUDENT = "student"
MESSAGE_SENDER_ASSISTANT = "assistant"
MESSAGE_SENDER_SYSTEM = "system"
MESSAGE_SENDER_STAFF = "staff"

MESSAGE_SENDERS = [MESSAGE_SENDER_STUDENT, MESSAGE_SENDER_ASSISTANT, MESSAGE_SENDER_SYSTEM, MESSAGE_SENDER_STAFF]


def new_message_doc(
    conversation_id,
    sender: str,
    content: str,
    intent: str | None = None,
    confidence: float | None = None,
    sources: list | None = None,
    requires_human_support: bool | None = None,
) -> dict:
    from datetime import datetime
    doc = {
        "conversation_id": conversation_id,
        "sender": sender,
        "content": content,
        "created_at": datetime.utcnow(),
    }
    if intent is not None:
        doc["intent"] = intent
    if confidence is not None:
        doc["confidence"] = float(confidence)
    if sources is not None:
        doc["sources"] = sources or []
    if requires_human_support is not None:
        doc["requires_human_support"] = bool(requires_human_support)
    return doc


def message_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    d["conversation_id"] = str(d["conversation_id"])
    return d

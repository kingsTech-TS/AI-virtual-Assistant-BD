from __future__ import annotations

NOTIFICATION_TYPES = [
    "ticket_created",
    "ticket_updated",
    "ticket_assigned",
    "ticket_resolved",
    "ticket_closed",
    "ticket_comment",
    "general",
    "announcement",
]


def new_notification_doc(
    user_id,
    title: str,
    message: str,
    type: str = "general",
    metadata: dict | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    return {
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": type,
        "metadata": metadata or {},
        "is_read": False,
        "created_at": utcnow(),
    }


def notification_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    if d.get("user_id"):
        d["user_id"] = str(d["user_id"])
    return d

from __future__ import annotations

ACTIONS = [
    "user_created",
    "user_updated",
    "user_deleted",
    "role_changed",
    "password_changed",
    "password_reset",
    "knowledge_created",
    "knowledge_updated",
    "knowledge_deleted",
    "knowledge_embedding_regenerated",
    "faq_created",
    "faq_updated",
    "faq_deleted",
    "ticket_created",
    "ticket_updated",
    "ticket_assigned",
    "department_created",
    "department_updated",
    "department_deleted",
    "logout",
]

RESOURCE_TYPES = [
    "user",
    "knowledge",
    "faq",
    "ticket",
    "department",
    "conversation",
    "message",
    "notification",
    "feedback",
]


def new_audit_log_doc(
    user_id=None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id=None,
    metadata: dict | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    return {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "metadata": metadata or {},
        "ip": ip,
        "user_agent": user_agent,
        "created_at": utcnow(),
    }


def audit_log_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["_id"] = str(d["_id"])
    if d.get("user_id"):
        d["user_id"] = str(d["user_id"])
    return d

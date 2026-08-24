from __future__ import annotations

from typing import Any

from app.constants.statuses import TicketStatus
from app.constants.priorities import TicketPriority


def new_ticket_doc(
    ticket_number: str,
    user_id,
    department_id,
    subject: str,
    description: str,
    category: str | None = None,
    priority: str = TicketPriority.MEDIUM,
) -> dict:
    from app.utils.helpers import utcnow
    now = utcnow()
    return {
        "ticket_number": ticket_number,
        "user_id": user_id,
        "department_id": department_id,
        "subject": subject,
        "description": description,
        "category": category,
        "priority": priority,
        "status": TicketStatus.OPEN,
        "assigned_to": None,
        "comments": [],
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }


def ticket_to_dict(doc: dict | None) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    if d.get("user_id"):
        d["user_id"] = str(d["user_id"])
    if d.get("department_id"):
        d["department_id"] = str(d["department_id"])
    if d.get("assigned_to"):
        d["assigned_to"] = str(d["assigned_to"])
    return d


def add_comment(doc: dict, user_id, author_name: str, author_role: str, text: str) -> None:
    from app.utils.helpers import utcnow
    comment = {
        "user_id": str(user_id),
        "author_name": author_name,
        "author_role": author_role,
        "text": text,
        "created_at": utcnow(),
    }
    comments = doc.setdefault("comments", [])
    comments.append(comment)

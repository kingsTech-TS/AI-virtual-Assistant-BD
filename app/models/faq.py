from __future__ import annotations

from app.constants.statuses import FAQStatus


def new_faq_doc(
    question: str,
    answer: str,
    category: str,
    created_by,
    status: str = FAQStatus.PUBLISHED,
) -> dict:
    from app.utils.helpers import utcnow
    now = utcnow()
    return {
        "question": question,
        "answer": answer,
        "category": category,
        "status": status,
        "view_count": 0,
        "helpful_count": 0,
        "created_by": created_by,
        "updated_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


def faq_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    if d.get("created_by"):
        d["created_by"] = str(d["created_by"])
    if d.get("updated_by"):
        d["updated_by"] = str(d["updated_by"])
    return d

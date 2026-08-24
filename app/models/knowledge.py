from __future__ import annotations

from app.constants.statuses import KnowledgeStatus


def new_knowledge_doc(
    title: str,
    content: str,
    category: str,
    created_by,
    department_id=None,
    faculty: str | None = None,
    source: str | None = None,
    status: str = KnowledgeStatus.PUBLISHED,
    embedding: list | None = None,
    metadata: dict | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    now = utcnow()
    doc = {
        "title": title,
        "content": content,
        "category": category,
        "department_id": department_id,
        "faculty": faculty,
        "source": source,
        "status": status,
        "embedding": embedding or [],
        "metadata": metadata or {},
        "created_by": created_by,
        "updated_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    return doc


def knowledge_to_dict(doc, include_embedding: bool = False) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    if d.get("department_id"):
        d["department_id"] = str(d["department_id"])
    if d.get("created_by"):
        d["created_by"] = str(d["created_by"])
    if d.get("updated_by"):
        d["updated_by"] = str(d["updated_by"])
    if not include_embedding:
        d.pop("embedding", None)
    return d

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from app.constants.statuses import KnowledgeStatus


def new_knowledge_doc(
    title: str,
    content: str,
    category: str,
    created_by=None,
    section: Optional[str] = None,
    document_id: Optional[str] = None,
    intent: Optional[List[str] | str] = None,
    page: Optional[int] = None,
    chunk_index: Optional[int] = 0,
    department_id=None,
    level: Optional[str] = None,
    faculty: Optional[str] = None,
    source: Optional[str] = None,
    status: str = KnowledgeStatus.PUBLISHED.value,
    version: int = 1,
    embedding: Optional[list] = None,
    metadata: Optional[dict] = None,
) -> dict:
    now = datetime.utcnow()
    intents_list = [intent] if isinstance(intent, str) else (intent or [])
    doc = {
        "document_id": document_id,
        "title": title,
        "section": section or "General",
        "category": category,
        "intent": intents_list,
        "content": content,
        "page": page,
        "chunk_index": chunk_index if chunk_index is not None else 0,
        "department_id": department_id,
        "level": level,
        "faculty": faculty,
        "source": source,
        "status": status,
        "version": version or 1,
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

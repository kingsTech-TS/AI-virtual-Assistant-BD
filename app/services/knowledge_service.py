from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.ai.embeddings import get_embeddings_provider
from app.core.exceptions import NotFound
from app.database.collections import KNOWLEDGE_BASE
from app.models.knowledge import knowledge_to_dict, new_knowledge_doc
from app.schemas.common import PaginationParams
from app.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.services.audit_service import audit_action
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def create(
    db,
    data: KnowledgeCreate,
    created_by_id,
) -> Dict[str, Any]:
    embeddings = get_embeddings_provider()
    content_to_embed = f"{data.title}\n\n{data.content}"
    embedding = await embeddings.embed_one(content_to_embed)

    created_by_oid = to_obj_id(created_by_id)
    doc = new_knowledge_doc(
        title=data.title,
        content=data.content,
        category=data.category,
        created_by=created_by_oid,
        department_id=to_obj_id(data.department_id),
        faculty=data.faculty,
        source=data.source,
        status=data.status.value if hasattr(data.status, "value") else data.status,
        embedding=embedding,
        metadata=data.metadata or {},
    )
    result = await db[KNOWLEDGE_BASE].insert_one(doc)
    doc["_id"] = result.inserted_id

    await audit_action(
        db,
        user_id=created_by_oid,
        action="knowledge_created",
        resource_type="knowledge",
        resource_id=result.inserted_id,
        metadata={"title": data.title, "category": data.category},
    )

    return knowledge_to_dict(doc, include_embedding=False)


async def list(
    db,
    pagination_params: PaginationParams,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[list[Dict[str, Any]], Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if filters:
        if filters.get("category"):
            query["category"] = filters["category"]
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("department_id"):
            query["department_id"] = to_obj_id(filters["department_id"])

    items, pagination = await paginate_cursor(
        db[KNOWLEDGE_BASE],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
    )

    result_items = [knowledge_to_dict(item, include_embedding=False) for item in items]
    return result_items, pagination


async def get(
    db,
    id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    doc = await db[KNOWLEDGE_BASE].find_one({"_id": oid})
    if not doc:
        raise NotFound(message="Knowledge entry not found", code="KNOWLEDGE_NOT_FOUND")
    return knowledge_to_dict(doc, include_embedding=False)


async def update(
    db,
    id,
    data: KnowledgeUpdate,
    updated_by_id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    updated_by_oid = to_obj_id(updated_by_id)

    existing = await db[KNOWLEDGE_BASE].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="Knowledge entry not found", code="KNOWLEDGE_NOT_FOUND")

    update_data: Dict[str, Any] = {"$set": {"updated_by": updated_by_oid, "updated_at": utcnow()}}

    if data.title is not None:
        update_data["$set"]["title"] = data.title
    if data.content is not None:
        update_data["$set"]["content"] = data.content
    if data.category is not None:
        update_data["$set"]["category"] = data.category
    if data.department_id is not None:
        update_data["$set"]["department_id"] = to_obj_id(data.department_id)
    if data.faculty is not None:
        update_data["$set"]["faculty"] = data.faculty
    if data.source is not None:
        update_data["$set"]["source"] = data.source
    if data.status is not None:
        update_data["$set"]["status"] = data.status.value if hasattr(data.status, "value") else data.status
    if data.metadata is not None:
        update_data["$set"]["metadata"] = data.metadata

    content_changed = data.content is not None and data.content != existing.get("content")
    title_changed = data.title is not None and data.title != existing.get("title")
    if content_changed or title_changed:
        new_title = data.title if data.title is not None else existing.get("title", "")
        new_content = data.content if data.content is not None else existing.get("content", "")
        embeddings = get_embeddings_provider()
        content_to_embed = f"{new_title}\n\n{new_content}"
        new_embedding = await embeddings.embed_one(content_to_embed)
        update_data["$set"]["embedding"] = new_embedding

    await db[KNOWLEDGE_BASE].update_one({"_id": oid}, update_data)

    updated = await db[KNOWLEDGE_BASE].find_one({"_id": oid})

    await audit_action(
        db,
        user_id=updated_by_oid,
        action="knowledge_updated",
        resource_type="knowledge",
        resource_id=oid,
        metadata={
            "changes": [k for k in update_data["$set"].keys() if k not in ("updated_by", "updated_at", "embedding")]
        },
    )

    return knowledge_to_dict(updated, include_embedding=False)


async def delete(
    db,
    id,
    deleter_id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    deleter_oid = to_obj_id(deleter_id)

    existing = await db[KNOWLEDGE_BASE].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="Knowledge entry not found", code="KNOWLEDGE_NOT_FOUND")

    await db[KNOWLEDGE_BASE].delete_one({"_id": oid})

    await audit_action(
        db,
        user_id=deleter_oid,
        action="knowledge_deleted",
        resource_type="knowledge",
        resource_id=oid,
        metadata={"title": existing.get("title"), "category": existing.get("category")},
    )

    return {"message": "Knowledge entry deleted successfully", "id": str(oid)}

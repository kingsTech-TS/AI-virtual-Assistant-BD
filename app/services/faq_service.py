from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.core.exceptions import NotFound
from app.database.collections import FAQS
from app.models.faq import faq_to_dict, new_faq_doc
from app.schemas.common import PaginationParams
from app.schemas.faq import FAQCreate, FAQUpdate
from app.services.audit_service import audit_action
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def create(
    db,
    data: FAQCreate,
    created_by_id,
) -> Dict[str, Any]:
    created_by_oid = to_obj_id(created_by_id)
    doc = new_faq_doc(
        question=data.question,
        answer=data.answer,
        category=data.category,
        created_by=created_by_oid,
        status=data.status.value if hasattr(data.status, "value") else data.status,
    )
    result = await db[FAQS].insert_one(doc)
    doc["_id"] = result.inserted_id

    await audit_action(
        db,
        user_id=created_by_oid,
        action="faq_created",
        resource_type="faq",
        resource_id=result.inserted_id,
        metadata={"question": data.question, "category": data.category},
    )

    return faq_to_dict(doc)


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

    items, pagination = await paginate_cursor(
        db[FAQS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
    )

    result_items = [faq_to_dict(item) for item in items]
    return result_items, pagination


async def get(
    db,
    id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    doc = await db[FAQS].find_one({"_id": oid})
    if not doc:
        raise NotFound(message="FAQ not found", code="FAQ_NOT_FOUND")
    return faq_to_dict(doc)


async def update(
    db,
    id,
    data: FAQUpdate,
    updated_by_id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    updated_by_oid = to_obj_id(updated_by_id)

    existing = await db[FAQS].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="FAQ not found", code="FAQ_NOT_FOUND")

    update_data: Dict[str, Any] = {"$set": {"updated_by": updated_by_oid, "updated_at": utcnow()}}

    if data.question is not None:
        update_data["$set"]["question"] = data.question
    if data.answer is not None:
        update_data["$set"]["answer"] = data.answer
    if data.category is not None:
        update_data["$set"]["category"] = data.category
    if data.status is not None:
        update_data["$set"]["status"] = data.status.value if hasattr(data.status, "value") else data.status

    await db[FAQS].update_one({"_id": oid}, update_data)

    updated = await db[FAQS].find_one({"_id": oid})

    await audit_action(
        db,
        user_id=updated_by_oid,
        action="faq_updated",
        resource_type="faq",
        resource_id=oid,
        metadata={
            "changes": [k for k in update_data["$set"].keys() if k not in ("updated_by", "updated_at")]
        },
    )

    return faq_to_dict(updated)


async def delete(
    db,
    id,
    deleter_id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    deleter_oid = to_obj_id(deleter_id)

    existing = await db[FAQS].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="FAQ not found", code="FAQ_NOT_FOUND")

    await db[FAQS].delete_one({"_id": oid})

    await audit_action(
        db,
        user_id=deleter_oid,
        action="faq_deleted",
        resource_type="faq",
        resource_id=oid,
        metadata={"question": existing.get("question"), "category": existing.get("category")},
    )

    return {"message": "FAQ deleted successfully", "id": str(oid)}

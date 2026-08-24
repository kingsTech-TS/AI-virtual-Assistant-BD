from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.core.exceptions import NotFound
from app.database.collections import DEPARTMENTS
from app.models.department import department_to_dict, new_department_doc
from app.schemas.common import PaginationParams
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.audit_service import audit_action
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def create(
    db,
    data: DepartmentCreate,
) -> Dict[str, Any]:
    doc = new_department_doc(
        name=data.name,
        code=data.code,
        faculty=data.faculty,
        description=data.description,
        support_email=str(data.support_email) if data.support_email else None,
    )
    result = await db[DEPARTMENTS].insert_one(doc)
    doc["_id"] = result.inserted_id

    await audit_action(
        db,
        user_id=None,
        action="department_created",
        resource_type="department",
        resource_id=result.inserted_id,
        metadata={"name": data.name, "code": data.code},
    )

    return department_to_dict(doc)


async def list(
    db,
    pagination_params: PaginationParams,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[list[Dict[str, Any]], Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if filters:
        is_active = filters.get("is_active")
        if is_active is not None:
            query["is_active"] = is_active

    items, pagination = await paginate_cursor(
        db[DEPARTMENTS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
    )

    result_items = [department_to_dict(item) for item in items]
    return result_items, pagination


async def get(
    db,
    id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)
    doc = await db[DEPARTMENTS].find_one({"_id": oid})
    if not doc:
        raise NotFound(message="Department not found", code="DEPARTMENT_NOT_FOUND")
    return department_to_dict(doc)


async def update(
    db,
    id,
    data: DepartmentUpdate,
) -> Dict[str, Any]:
    oid = to_obj_id(id)

    existing = await db[DEPARTMENTS].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="Department not found", code="DEPARTMENT_NOT_FOUND")

    update_data: Dict[str, Any] = {"$set": {"updated_at": utcnow()}}

    if data.name is not None:
        update_data["$set"]["name"] = data.name
    if data.code is not None:
        update_data["$set"]["code"] = data.code.upper() if data.code else data.code
    if data.faculty is not None:
        update_data["$set"]["faculty"] = data.faculty
    if data.description is not None:
        update_data["$set"]["description"] = data.description
    if data.support_email is not None:
        update_data["$set"]["support_email"] = str(data.support_email)
    if data.is_active is not None:
        update_data["$set"]["is_active"] = data.is_active

    await db[DEPARTMENTS].update_one({"_id": oid}, update_data)

    updated = await db[DEPARTMENTS].find_one({"_id": oid})

    await audit_action(
        db,
        user_id=None,
        action="department_updated",
        resource_type="department",
        resource_id=oid,
        metadata={
            "changes": [k for k in update_data["$set"].keys() if k != "updated_at"]
        },
    )

    return department_to_dict(updated)


async def delete(
    db,
    id,
) -> Dict[str, Any]:
    oid = to_obj_id(id)

    existing = await db[DEPARTMENTS].find_one({"_id": oid})
    if not existing:
        raise NotFound(message="Department not found", code="DEPARTMENT_NOT_FOUND")

    await db[DEPARTMENTS].delete_one({"_id": oid})

    await audit_action(
        db,
        user_id=None,
        action="department_deleted",
        resource_type="department",
        resource_id=oid,
        metadata={"name": existing.get("name"), "code": existing.get("code")},
    )

    return {"message": "Department deleted successfully", "id": str(oid)}

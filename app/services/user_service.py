from __future__ import annotations

from typing import Any, Dict, Optional

from app.constants.roles import UserRole, has_min_role
from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.core.security import hash_password, verify_password
from app.database.collections import USERS
from app.models.user import user_to_dict
from app.schemas.common import PaginationParams
from app.schemas.user import AdminUserUpdateRequest, UserUpdateRequest
from app.services.audit_service import audit_action
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def get_user_by_id(db, user_id: Any) -> Dict[str, Any]:
    oid = to_obj_id(user_id)
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    return user_to_dict(user)


async def list_users(
    db,
    pagination_params: PaginationParams,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    query = dict(filters or {})
    if "email" in query and query["email"]:
        query["email"] = query["email"].lower()
    if "role" in query and not query["role"]:
        del query["role"]
    if "is_active" in query and query["is_active"] is None:
        del query["is_active"]
    if "department_id" in query:
        query["department_id"] = to_obj_id(query["department_id"])
        if query["department_id"] is None:
            del query["department_id"]
    items, pagination = await paginate_cursor(
        db[USERS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )
    return {
        "items": [user_to_dict(it) for it in items],
        "pagination": pagination,
    }


async def update_user(
    db,
    user_id: Any,
    data: AdminUserUpdateRequest,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    current_role = current_user.get("role")
    if not has_min_role(current_role, UserRole.ADMIN):
        raise Forbidden(message="Only admins can update users", code="ADMIN_REQUIRED")

    oid = to_obj_id(user_id)
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    update_data: Dict[str, Any] = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.email is not None:
        new_email = data.email.lower()
        existing = await db[USERS].find_one({"email": new_email, "_id": {"$ne": oid}})
        if existing:
            raise BadRequest(message="Email already in use", code="EMAIL_TAKEN")
        update_data["email"] = new_email
    if data.department_id is not None:
        update_data["department_id"] = to_obj_id(data.department_id)
    if data.faculty is not None:
        update_data["faculty"] = data.faculty
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.role is not None:
        target_role = data.role.value if hasattr(data.role, "value") else data.role
        if not has_min_role(current_role, target_role):
            raise Forbidden(
                message="Cannot assign a role higher than your own",
                code="INSUFFICIENT_ROLE_PRIVILEGE",
            )
        update_data["role"] = target_role
    if data.is_active is not None:
        update_data["is_active"] = data.is_active

    if not update_data:
        return user_to_dict(user)

    update_data["updated_at"] = utcnow()

    await db[USERS].update_one({"_id": oid}, {"$set": update_data})

    updated = await db[USERS].find_one({"_id": oid})
    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="user_updated",
        resource_type="user",
        resource_id=oid,
        metadata={"changes": list(update_data.keys())},
    )
    return user_to_dict(updated)


async def update_me(
    db,
    current_user: Dict[str, Any],
    data: UserUpdateRequest,
) -> Dict[str, Any]:
    oid = to_obj_id(current_user.get("_id"))
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    update_data: Dict[str, Any] = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.faculty is not None:
        update_data["faculty"] = data.faculty
    if data.department_id is not None:
        update_data["department_id"] = to_obj_id(data.department_id)

    if data.new_password is not None:
        if not data.current_password:
            raise BadRequest(
                message="Current password is required to change password",
                code="CURRENT_PASSWORD_REQUIRED",
            )
        if not verify_password(data.current_password, user.get("password_hash") or ""):
            raise BadRequest(
                message="Current password is incorrect",
                code="CURRENT_PASSWORD_INCORRECT",
            )
        update_data["password_hash"] = hash_password(data.new_password)

    if not update_data:
        return user_to_dict(user)

    update_data["updated_at"] = utcnow()

    await db[USERS].update_one({"_id": oid}, {"$set": update_data})

    updated = await db[USERS].find_one({"_id": oid})
    changes = list(update_data.keys())
    if "password_hash" in changes:
        changes.remove("password_hash")
        changes.append("password")
    await audit_action(
        db,
        user_id=oid,
        action="profile_updated",
        resource_type="user",
        resource_id=oid,
        metadata={"changes": changes},
    )
    return user_to_dict(updated)

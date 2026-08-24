from __future__ import annotations

from typing import Any, Callable, Dict

from app.constants.roles import UserRole, has_min_role
from app.core.exceptions import Forbidden, NotFound
from app.database.collections import CONVERSATIONS, TICKETS
from app.dependencies.auth import get_current_active_user, require_roles
from app.utils.ids import to_obj_id


def require_student() -> Callable:
    """Requires at least Student role (any active user)."""
    return require_roles(UserRole.STUDENT, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)


def require_staff() -> Callable:
    """Requires at least Staff role."""
    return require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)


def require_admin() -> Callable:
    """Requires at least Admin role."""
    return require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


def require_super_admin() -> Callable:
    """Requires Super Admin role exclusively."""
    return require_roles(UserRole.SUPER_ADMIN)


def require_staff_or_admin() -> Callable:
    """Requires Staff, Admin, or Super Admin role."""
    return require_roles(UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN)


def require_admin_or_super_admin() -> Callable:
    """Requires Admin or Super Admin role."""
    return require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


async def ensure_conversation_owner_or_admin(
    db,
    conversation_id: Any,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    oid = to_obj_id(conversation_id)
    if not oid:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    conv = await db[CONVERSATIONS].find_one({"_id": oid})
    if not conv:
        raise NotFound(message="Conversation not found", code="CONVERSATION_NOT_FOUND")
    user_role = current_user.get("role")
    is_admin = has_min_role(user_role, UserRole.ADMIN)
    is_owner = str(conv.get("user_id")) == str(current_user.get("_id"))
    if not (is_admin or is_owner):
        raise Forbidden(message="You do not have access to this conversation", code="CONVERSATION_FORBIDDEN")
    return conv


async def ensure_ticket_access(
    db,
    ticket_id: Any,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    if not oid:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")
    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    user_role = current_user.get("role")
    uid = str(current_user.get("_id"))
    ticket_user = str(ticket.get("user_id"))
    ticket_dept = str(ticket.get("department_id")) if ticket.get("department_id") else None
    user_dept = str(current_user.get("department_id")) if current_user.get("department_id") else None
    assigned_to = str(ticket.get("assigned_to")) if ticket.get("assigned_to") else None

    # Admin and Super Admin have full system-wide visibility
    if has_min_role(user_role, UserRole.ADMIN):
        return ticket
    # Ticket creator can always access their own ticket
    if uid == ticket_user:
        return ticket
    # Staff can access if explicitly assigned OR belongs to their department
    if user_role == UserRole.STAFF.value:
        if assigned_to == uid or (ticket_dept and user_dept and ticket_dept == user_dept):
            return ticket
    raise Forbidden(message="You do not have permission to access this ticket", code="TICKET_FORBIDDEN")


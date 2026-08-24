from __future__ import annotations

from typing import Any, Dict

from app.constants.roles import UserRole
from app.constants.statuses import TicketStatus, is_valid_ticket_transition
from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.database.collections import TICKETS, USERS, DEPARTMENTS
from app.models.ticket import new_ticket_doc, ticket_to_dict, add_comment
from app.utils.helpers import utcnow, generate_ticket_number
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


def _get_ticket_scope_query(current_user: Dict[str, Any]) -> Dict[str, Any]:
    role = current_user.get("role")
    user_oid = to_obj_id(current_user.get("_id"))
    if role == UserRole.STUDENT.value:
        return {"user_id": user_oid}
    if role == UserRole.STAFF.value:
        dept_oid = to_obj_id(current_user.get("department_id"))
        if dept_oid:
            return {"$or": [{"assigned_to": user_oid}, {"department_id": dept_oid}]}
        return {"assigned_to": user_oid}
    return {}


async def create(
    db,
    current_user: Dict[str, Any],
    data,
) -> Dict[str, Any]:
    user_oid = to_obj_id(current_user.get("_id"))
    dept_oid = to_obj_id(data.department_id) or to_obj_id(current_user.get("department_id"))
    ticket_number = generate_ticket_number()
    doc = new_ticket_doc(
        ticket_number=ticket_number,
        user_id=user_oid,
        department_id=dept_oid,
        subject=data.subject,
        description=data.description,
        category=data.category,
        priority=data.priority.value if hasattr(data.priority, "value") else data.priority,
    )
    result = await db[TICKETS].insert_one(doc)
    doc["_id"] = result.inserted_id
    ticket_id = str(result.inserted_id)

    from app.services import notification_service

    await notification_service.create(
        db,
        user_id=user_oid,
        title="Ticket Created Successfully",
        message=f"Your ticket {ticket_number} has been submitted. We will respond shortly.",
        type="ticket_created",
        metadata={"ticket_id": ticket_id, "ticket_number": ticket_number},
    )

    if dept_oid:
        dept_staff = await db[USERS].find({
            "department_id": dept_oid,
            "role": {"$in": [UserRole.STAFF.value, UserRole.ADMIN.value]},
            "is_active": True,
        }).to_list(length=None)
        for staff in dept_staff:
            await notification_service.create(
                db,
                user_id=staff["_id"],
                title="New Ticket Received",
                message=f"A new ticket {ticket_number} has been created in your department.",
                type="ticket_created",
                metadata={"ticket_id": ticket_id, "ticket_number": ticket_number},
            )

    from app.services.audit_service import audit_action

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_created",
        resource_type="ticket",
        resource_id=result.inserted_id,
        metadata={"ticket_number": ticket_number},
    )

    return ticket_to_dict(doc)


async def list(
    db,
    current_user: Dict[str, Any],
    pagination_params,
    filters: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    query = _get_ticket_scope_query(current_user)
    if filters:
        for key, value in filters.items():
            if value is not None:
                if key in ("status", "priority", "department_id"):
                    if key == "department_id":
                        query["department_id"] = to_obj_id(value)
                    else:
                        query[key] = value
                elif key == "assigned_to":
                    query["assigned_to"] = to_obj_id(value)
    items, pagination = await paginate_cursor(
        db[TICKETS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )
    items_dicts = [ticket_to_dict(item) for item in items]
    return {"items": items_dicts, "pagination": pagination}


async def get(
    db,
    current_user: Dict[str, Any],
    ticket_id,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found")
    scope_query = _get_ticket_scope_query(current_user)
    if scope_query:
        combined = {"_id": oid, **scope_query}
        check = await db[TICKETS].find_one(combined)
        if not check:
            raise Forbidden(message="You do not have permission to view this ticket")
    return ticket_to_dict(ticket)


async def update(
    db,
    current_user: Dict[str, Any],
    ticket_id,
    data,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))
    role = current_user.get("role")

    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found")

    scope_query = _get_ticket_scope_query(current_user)
    if scope_query:
        combined = {"_id": oid, **scope_query}
        check = await db[TICKETS].find_one(combined)
        if not check:
            raise Forbidden(message="You do not have permission to update this ticket")

    updates: Dict[str, Any] = {}
    audit_metadata: Dict[str, Any] = {}

    is_staff_or_above = role in (UserRole.STAFF.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)
    is_student = role == UserRole.STUDENT.value

    if data.subject is not None and is_staff_or_above:
        updates["subject"] = data.subject
        audit_metadata["subject"] = data.subject

    if data.description is not None:
        if is_student or is_staff_or_above:
            updates["description"] = data.description
            audit_metadata["description_updated"] = True

    if data.category is not None and is_staff_or_above:
        updates["category"] = data.category
        audit_metadata["category"] = data.category

    if data.status is not None:
        current_status = TicketStatus(ticket.get("status", TicketStatus.OPEN))
        new_status = TicketStatus(data.status.value) if hasattr(data.status, "value") else TicketStatus(data.status)
        if is_student:
            if not (current_status == TicketStatus.WAITING_FOR_STUDENT and new_status == TicketStatus.IN_PROGRESS):
                raise Forbidden(message="Students can only transition status from waiting_for_student to in_progress")
        if not is_valid_ticket_transition(current_status, new_status):
            raise BadRequest(
                message=f"Invalid status transition from {current_status.value} to {new_status.value}"
            )
        updates["status"] = new_status.value
        audit_metadata["status"] = {"from": current_status.value, "to": new_status.value}
        if new_status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            updates["resolved_at"] = utcnow()

    if data.priority is not None and is_staff_or_above:
        priority_val = data.priority.value if hasattr(data.priority, "value") else data.priority
        updates["priority"] = priority_val
        audit_metadata["priority"] = priority_val

    if data.assigned_to is not None and is_staff_or_above:
        assignee_oid = to_obj_id(data.assigned_to)
        assignee = await db[USERS].find_one({"_id": assignee_oid})
        if not assignee:
            raise NotFound(message="Assigned user not found")
        ticket_dept = ticket.get("department_id")
        assignee_dept = assignee.get("department_id")
        if str(ticket_dept) != str(assignee_dept):
            raise BadRequest(message="Assigned staff must belong to the ticket's department")
        if assignee.get("role") not in (UserRole.STAFF.value, UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value):
            raise BadRequest(message="Only staff, admin, or super_admin can be assigned tickets")
        updates["assigned_to"] = assignee_oid
        audit_metadata["assigned_to"] = str(assignee_oid)

    updated_doc = dict(ticket)
    if data.comment is not None:
        author_name = current_user.get("name", "Unknown")
        author_role = role or UserRole.STUDENT.value
        add_comment(updated_doc, user_oid, author_name, author_role, data.comment)
        updates["comments"] = updated_doc.get("comments", [])
        audit_metadata["comment_added"] = True

    if updates:
        updates["updated_at"] = utcnow()
        await db[TICKETS].update_one({"_id": oid}, {"$set": updates})
        updated_doc.update(updates)

    from app.services.audit_service import audit_action

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_updated",
        resource_type="ticket",
        resource_id=oid,
        metadata=audit_metadata,
    )

    from app.services import notification_service

    await notification_service.create(
        db,
        user_id=ticket.get("user_id"),
        title="Ticket Updated",
        message=f"Your ticket {ticket.get('ticket_number')} has been updated.",
        type="ticket_updated",
        metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number"), **audit_metadata},
    )

    return ticket_to_dict(updated_doc)

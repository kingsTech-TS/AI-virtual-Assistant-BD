#!/usr/bin/env python3
"""
Staff Service Layer.
Encapsulates human support, ticket triage, communication, and dashboard metrics for Staff.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.constants.priorities import TicketPriority
from app.constants.roles import UserRole
from app.constants.statuses import TicketStatus
from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.database.collections import TICKETS, USERS
from app.models.ticket import add_comment, ticket_to_dict
from app.services.audit_service import audit_action
from app.services import notification_service
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


def _get_staff_scope_query(current_user: Dict[str, Any]) -> Dict[str, Any]:
    user_oid = to_obj_id(current_user.get("_id"))
    dept_oid = to_obj_id(current_user.get("department_id"))
    if dept_oid:
        return {"$or": [{"assigned_to": user_oid}, {"department_id": dept_oid}]}
    return {"assigned_to": user_oid}


async def _enrich_ticket_with_student_info(db, ticket_dict: Dict[str, Any]) -> Dict[str, Any]:
    user_id = ticket_dict.get("user_id")
    if user_id:
        user_oid = to_obj_id(user_id)
        if user_oid:
            student = await db[USERS].find_one({"_id": user_oid})
            if student:
                ticket_dict["student_name"] = student.get("name")
                ticket_dict["student_email"] = student.get("email")
                ticket_dict["student_matric_number"] = student.get("matric_number")
                ticket_dict["student_faculty"] = student.get("faculty")
    return ticket_dict


async def get_dashboard(db, current_user: Dict[str, Any]) -> Dict[str, Any]:
    user_oid = to_obj_id(current_user.get("_id"))
    scope_query = _get_staff_scope_query(current_user)

    assigned_count = await db[TICKETS].count_documents({
        "assigned_to": user_oid,
        "status": {"$in": [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.WAITING_FOR_STUDENT.value]},
    })

    open_count = await db[TICKETS].count_documents({
        **scope_query,
        "status": TicketStatus.OPEN.value,
    })

    in_progress_count = await db[TICKETS].count_documents({
        **scope_query,
        "status": TicketStatus.IN_PROGRESS.value,
    })

    waiting_count = await db[TICKETS].count_documents({
        **scope_query,
        "status": TicketStatus.WAITING_FOR_STUDENT.value,
    })

    resolved_count = await db[TICKETS].count_documents({
        **scope_query,
        "status": TicketStatus.RESOLVED.value,
    })

    urgent_count = await db[TICKETS].count_documents({
        **scope_query,
        "priority": {"$in": [TicketPriority.HIGH.value, TicketPriority.URGENT.value]},
        "status": {"$ne": TicketStatus.CLOSED.value},
    })

    # Recent tickets
    recent_docs = await db[TICKETS].find(scope_query).sort("created_at", -1).limit(5).to_list(length=5)
    recent_tickets = [ticket_to_dict(doc) for doc in recent_docs]

    return {
        "statistics": {
            "assigned": assigned_count,
            "open": open_count,
            "in_progress": in_progress_count,
            "waiting_for_student": waiting_count,
            "resolved": resolved_count,
            "urgent": urgent_count,
        },
        "recent_tickets": recent_tickets,
    }


async def list_tickets(
    db,
    current_user: Dict[str, Any],
    pagination_params,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    scope_query = _get_staff_scope_query(current_user)
    query = dict(scope_query)

    if filters:
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("priority"):
            query["priority"] = filters["priority"]
        if filters.get("assigned_only"):
            query["assigned_to"] = to_obj_id(current_user.get("_id"))

    items, pagination = await paginate_cursor(
        db[TICKETS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )

    tickets = [ticket_to_dict(item) for item in items]
    return {"items": tickets, "pagination": pagination}


async def get_ticket(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    if not oid:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    user_role = current_user.get("role")
    uid = str(current_user.get("_id"))
    assigned_to = str(ticket.get("assigned_to")) if ticket.get("assigned_to") else None
    ticket_dept = str(ticket.get("department_id")) if ticket.get("department_id") else None
    user_dept = str(current_user.get("department_id")) if current_user.get("department_id") else None

    is_admin = user_role in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value)
    is_assigned = assigned_to == uid
    is_same_dept = ticket_dept and user_dept and ticket_dept == user_dept

    if not (is_admin or is_assigned or is_same_dept):
        raise Forbidden(message="You do not have permission to view tickets outside your department", code="TICKET_FORBIDDEN")

    ticket_dict = ticket_to_dict(ticket)
    return await _enrich_ticket_with_student_info(db, ticket_dict)


async def update_ticket(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    data,
) -> Dict[str, Any]:
    ticket = await get_ticket(db, current_user, ticket_id)
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))

    updates: Dict[str, Any] = {}
    audit_meta: Dict[str, Any] = {}

    if hasattr(data, "status") and data.status is not None:
        status_val = data.status.value if hasattr(data.status, "value") else data.status
        updates["status"] = status_val
        audit_meta["status"] = status_val
        if status_val in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
            updates["resolved_at"] = utcnow()

    if hasattr(data, "priority") and data.priority is not None:
        priority_val = data.priority.value if hasattr(data.priority, "value") else data.priority
        updates["priority"] = priority_val
        audit_meta["priority"] = priority_val

    if hasattr(data, "category") and data.category is not None:
        updates["category"] = data.category
        audit_meta["category"] = data.category

    if hasattr(data, "comment") and data.comment:
        doc = await db[TICKETS].find_one({"_id": oid})
        add_comment(doc, user_oid, current_user.get("name", "Staff Member"), UserRole.STAFF.value, data.comment)
        updates["comments"] = doc.get("comments", [])
        audit_meta["comment_added"] = True

    if updates:
        updates["updated_at"] = utcnow()
        await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_updated",
        resource_type="ticket",
        resource_id=oid,
        metadata=audit_meta,
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def respond(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    message: str,
) -> Dict[str, Any]:
    ticket = await get_ticket(db, current_user, ticket_id)
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))

    if not message or not message.strip():
        raise BadRequest(message="Response message cannot be empty", code="EMPTY_MESSAGE")

    doc = await db[TICKETS].find_one({"_id": oid})
    add_comment(
        doc,
        user_id=user_oid,
        author_name=current_user.get("name", "Staff Member"),
        author_role=UserRole.STAFF.value,
        text=message.strip(),
    )

    updates = {
        "comments": doc["comments"],
        "status": TicketStatus.WAITING_FOR_STUDENT.value,
        "updated_at": utcnow(),
    }
    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    # Notify student
    student_id = to_obj_id(ticket.get("user_id"))
    if student_id:
        await notification_service.create(
            db,
            user_id=student_id,
            title="Ticket Response Received",
            message=f"You have received a response to ticket {ticket.get('ticket_number')}.",
            type="ticket_response",
            metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number")},
        )

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_response_added",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number")},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def assign_to_self(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
) -> Dict[str, Any]:
    ticket = await get_ticket(db, current_user, ticket_id)
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))

    updates = {
        "assigned_to": user_oid,
        "status": TicketStatus.IN_PROGRESS.value if ticket.get("status") == TicketStatus.OPEN.value else ticket.get("status"),
        "updated_at": utcnow(),
    }
    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_assigned_self",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number"), "staff_id": str(user_oid)},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def escalate(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    reason: Optional[str] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    ticket = await get_ticket(db, current_user, ticket_id)
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))

    new_priority = priority or TicketPriority.URGENT.value
    doc = await db[TICKETS].find_one({"_id": oid})

    escalate_note = f"[ESCALATED by {current_user.get('name', 'Staff')}]: {reason or 'Issue requires higher level intervention.'}"
    add_comment(doc, user_oid, current_user.get("name", "Staff"), UserRole.STAFF.value, escalate_note)

    updates = {
        "priority": new_priority,
        "comments": doc["comments"],
        "updated_at": utcnow(),
    }
    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_escalated",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number"), "priority": new_priority, "reason": reason},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def resolve(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    resolution_note: Optional[str] = None,
) -> Dict[str, Any]:
    ticket = await get_ticket(db, current_user, ticket_id)
    oid = to_obj_id(ticket_id)
    user_oid = to_obj_id(current_user.get("_id"))

    doc = await db[TICKETS].find_one({"_id": oid})
    if resolution_note:
        note_text = f"[RESOLUTION NOTE]: {resolution_note}"
        add_comment(doc, user_oid, current_user.get("name", "Staff"), UserRole.STAFF.value, note_text)

    updates = {
        "status": TicketStatus.RESOLVED.value,
        "resolved_at": utcnow(),
        "comments": doc.get("comments", []),
        "updated_at": utcnow(),
    }
    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    # Notify student
    student_id = to_obj_id(ticket.get("user_id"))
    if student_id:
        await notification_service.create(
            db,
            user_id=student_id,
            title="Ticket Resolved",
            message=f"Your ticket {ticket.get('ticket_number')} has been resolved.",
            type="ticket_resolved",
            metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number")},
        )

    await audit_action(
        db,
        user_id=user_oid,
        action="ticket_resolved",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number")},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)

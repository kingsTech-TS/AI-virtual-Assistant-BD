#!/usr/bin/env python3
"""
Admin Service Layer.
Comprehensive system management including user management, staff management,
ticket management, knowledge ingestion, analytics, and system audit logs.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from app.ai.embeddings import get_embeddings_provider
from app.constants.priorities import TicketPriority
from app.constants.roles import UserRole
from app.constants.statuses import FAQStatus, KnowledgeStatus, TicketStatus
from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.core.security import hash_password
from app.database.collections import (
    AUDIT_LOGS,
    CONVERSATIONS,
    DEPARTMENTS,
    FAQS,
    FEEDBACK,
    KNOWLEDGE_BASE,
    MESSAGES,
    TICKETS,
    USERS,
)
from app.models.department import department_to_dict
from app.models.knowledge import knowledge_to_dict, new_knowledge_doc
from app.models.ticket import add_comment, ticket_to_dict
from app.models.user import new_user_doc, user_to_dict
from app.services.audit_service import audit_action
from app.services import notification_service
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def get_dashboard(db) -> Dict[str, Any]:
    # Users breakdown
    students_count = await db[USERS].count_documents({"role": UserRole.STUDENT.value})
    staff_count = await db[USERS].count_documents({"role": UserRole.STAFF.value})
    admins_count = await db[USERS].count_documents({
        "role": {"$in": [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]}
    })
    total_users = students_count + staff_count + admins_count

    # Tickets breakdown
    total_tickets = await db[TICKETS].count_documents({})
    open_tickets = await db[TICKETS].count_documents({"status": TicketStatus.OPEN.value})
    in_progress_tickets = await db[TICKETS].count_documents({"status": TicketStatus.IN_PROGRESS.value})
    waiting_tickets = await db[TICKETS].count_documents({"status": TicketStatus.WAITING_FOR_STUDENT.value})
    resolved_tickets = await db[TICKETS].count_documents({"status": TicketStatus.RESOLVED.value})
    closed_tickets = await db[TICKETS].count_documents({"status": TicketStatus.CLOSED.value})

    # Chatbot metrics
    conversations_count = await db[CONVERSATIONS].count_documents({})
    messages_count = await db[MESSAGES].count_documents({})
    escalations_count = await db[MESSAGES].count_documents({"requires_human_support": True})

    # Knowledge & FAQs
    knowledge_total = await db[KNOWLEDGE_BASE].count_documents({})
    knowledge_published = await db[KNOWLEDGE_BASE].count_documents({"status": KnowledgeStatus.PUBLISHED.value})
    faqs_total = await db[FAQS].count_documents({})

    # Departments
    departments_total = await db[DEPARTMENTS].count_documents({})
    departments_active = await db[DEPARTMENTS].count_documents({"is_active": True})

    # Feedback metrics
    positive_fb = await db[FEEDBACK].count_documents({"rating": {"$in": ["thumbs_up", "positive", "5", "4"]}})
    negative_fb = await db[FEEDBACK].count_documents({"rating": {"$in": ["thumbs_down", "negative", "1", "2"]}})

    return {
        "users": {
            "students": students_count,
            "staff": staff_count,
            "admins": admins_count,
            "total": total_users,
        },
        "tickets": {
            "total": total_tickets,
            "open": open_tickets,
            "in_progress": in_progress_tickets,
            "waiting_for_student": waiting_tickets,
            "resolved": resolved_tickets,
            "closed": closed_tickets,
            "unresolved": open_tickets + in_progress_tickets + waiting_tickets,
        },
        "chatbot": {
            "conversations": conversations_count,
            "messages": messages_count,
            "escalations": escalations_count,
        },
        "knowledge": {
            "total": knowledge_total,
            "published": knowledge_published,
            "faqs": faqs_total,
        },
        "departments": {
            "total": departments_total,
            "active": departments_active,
        },
        "feedback": {
            "positive": positive_fb,
            "negative": negative_fb,
        },
    }


# ============================================================================
# USER & STAFF MANAGEMENT
# ============================================================================

async def list_users(
    db,
    pagination_params,
    role: Optional[str] = None,
    search: Optional[str] = None,
    department_id: Optional[str] = None,
) -> Dict[str, Any]:
    query: Dict[str, Any] = {}
    if role:
        query["role"] = role
    if department_id:
        query["department_id"] = to_obj_id(department_id)
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"matric_number": {"$regex": search, "$options": "i"}},
            {"staff_id": {"$regex": search, "$options": "i"}},
        ]

    items, pagination = await paginate_cursor(
        db[USERS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )

    users = [user_to_dict(u) for u in items]
    return {"items": users, "pagination": pagination}


async def get_user_by_id(db, user_id: str) -> Dict[str, Any]:
    oid = to_obj_id(user_id)
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    return user_to_dict(user)


async def create_user(
    db,
    data,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    caller_role = current_user.get("role")
    requested_role = data.role.value if hasattr(data.role, "value") else data.role

    # Only super_admin can create super_admin accounts
    if requested_role == UserRole.SUPER_ADMIN.value and caller_role != UserRole.SUPER_ADMIN.value:
        raise Forbidden(message="Only Super Admin can create Super Admin accounts", code="SUPER_ADMIN_REQUIRED")

    existing = await db[USERS].find_one({"email": data.email.lower()})
    if existing:
        raise Conflict(message="A user with this email already exists", code="EMAIL_TAKEN")

    if getattr(data, "matric_number", None):
        dup = await db[USERS].find_one({"matric_number": data.matric_number})
        if dup:
            raise Conflict(message="Matric number already registered", code="MATRIC_TAKEN")

    if getattr(data, "staff_id", None):
        dup_staff = await db[USERS].find_one({"staff_id": data.staff_id})
        if dup_staff:
            raise Conflict(message="Staff ID already registered", code="STAFF_ID_TAKEN")

    doc = new_user_doc(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=requested_role,
        matric_number=getattr(data, "matric_number", None),
        staff_id=getattr(data, "staff_id", None),
        department_id=to_obj_id(getattr(data, "department_id", None)),
        faculty=getattr(data, "faculty", None),
        phone=getattr(data, "phone", None),
        position=getattr(data, "position", None),
        permissions=getattr(data, "permissions", []),
    )

    result = await db[USERS].insert_one(doc)
    doc["_id"] = result.inserted_id

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="user_created",
        resource_type="user",
        resource_id=result.inserted_id,
        metadata={"role": requested_role, "email": data.email.lower(), "created_by": str(current_user.get("_id"))},
    )

    return user_to_dict(doc)


async def update_user(
    db,
    user_id: str,
    data,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    oid = to_obj_id(user_id)
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    target_user = await db[USERS].find_one({"_id": oid})
    if not target_user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    caller_role = current_user.get("role")
    target_role = target_user.get("role")

    # If target is super_admin, caller must be super_admin
    if target_role == UserRole.SUPER_ADMIN.value and caller_role != UserRole.SUPER_ADMIN.value:
        raise Forbidden(message="Only Super Admin can modify Super Admin accounts", code="SUPER_ADMIN_REQUIRED")

    updates: Dict[str, Any] = {}
    audit_meta: Dict[str, Any] = {}

    if hasattr(data, "name") and data.name is not None:
        updates["name"] = data.name
    if hasattr(data, "email") and data.email is not None:
        existing = await db[USERS].find_one({"email": data.email.lower(), "_id": {"$ne": oid}})
        if existing:
            raise Conflict(message="Email already in use", code="EMAIL_TAKEN")
        updates["email"] = data.email.lower()
    if hasattr(data, "role") and data.role is not None:
        new_role_val = data.role.value if hasattr(data.role, "value") else data.role
        if new_role_val == UserRole.SUPER_ADMIN.value and caller_role != UserRole.SUPER_ADMIN.value:
            raise Forbidden(message="Only Super Admin can promote users to Super Admin", code="SUPER_ADMIN_REQUIRED")
        updates["role"] = new_role_val
        audit_meta["role_change"] = {"from": target_role, "to": new_role_val}
    if hasattr(data, "is_active") and data.is_active is not None:
        updates["is_active"] = data.is_active
        audit_meta["is_active"] = data.is_active
    if hasattr(data, "department_id"):
        updates["department_id"] = to_obj_id(data.department_id) if data.department_id else None
    if hasattr(data, "faculty") and data.faculty is not None:
        updates["faculty"] = data.faculty
    if hasattr(data, "phone") and data.phone is not None:
        updates["phone"] = data.phone
    if hasattr(data, "staff_id") and data.staff_id is not None:
        updates["staff_id"] = data.staff_id
    if hasattr(data, "position") and data.position is not None:
        updates["position"] = data.position
    if hasattr(data, "permissions") and data.permissions is not None:
        updates["permissions"] = data.permissions

    if updates:
        updates["updated_at"] = utcnow()
        await db[USERS].update_one({"_id": oid}, {"$set": updates})

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="user_updated",
        resource_type="user",
        resource_id=oid,
        metadata=audit_meta or {"updated_fields": list(updates.keys())},
    )

    updated_doc = await db[USERS].find_one({"_id": oid})
    return user_to_dict(updated_doc)


async def delete_user(
    db,
    user_id: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    oid = to_obj_id(user_id)
    if not oid:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    caller_id = str(current_user.get("_id"))
    if str(oid) == caller_id:
        raise BadRequest(message="You cannot delete your own account", code="CANNOT_DELETE_SELF")

    target = await db[USERS].find_one({"_id": oid})
    if not target:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")

    caller_role = current_user.get("role")
    if target.get("role") == UserRole.SUPER_ADMIN.value and caller_role != UserRole.SUPER_ADMIN.value:
        raise Forbidden(message="Only Super Admin can delete a Super Admin account", code="SUPER_ADMIN_REQUIRED")

    await db[USERS].delete_one({"_id": oid})

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="user_deleted",
        resource_type="user",
        resource_id=oid,
        metadata={"email": target.get("email"), "role": target.get("role")},
    )

    return {"message": "User deleted successfully", "id": str(oid)}


# ============================================================================
# TICKET MANAGEMENT (ADMIN FULL ACCESS)
# ============================================================================

async def list_admin_tickets(
    db,
    pagination_params,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    query: Dict[str, Any] = {}
    if filters:
        if filters.get("status"):
            query["status"] = filters["status"]
        if filters.get("priority"):
            query["priority"] = filters["priority"]
        if filters.get("department_id"):
            query["department_id"] = to_obj_id(filters["department_id"])
        if filters.get("assigned_to"):
            query["assigned_to"] = to_obj_id(filters["assigned_to"])

    items, pagination = await paginate_cursor(
        db[TICKETS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )

    tickets = [ticket_to_dict(item) for item in items]
    return {"items": tickets, "pagination": pagination}


async def get_admin_ticket(db, ticket_id: str) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    if not oid:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")
    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    d = ticket_to_dict(ticket)
    # Add student info
    user_id = d.get("user_id")
    if user_id:
        student = await db[USERS].find_one({"_id": to_obj_id(user_id)})
        if student:
            d["student_name"] = student.get("name")
            d["student_email"] = student.get("email")
            d["student_matric_number"] = student.get("matric_number")
    return d


async def assign_ticket(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    assigned_to: str,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    staff_oid = to_obj_id(assigned_to)
    if not oid or not staff_oid:
        raise BadRequest(message="Invalid ticket ID or staff ID", code="INVALID_ID")

    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    staff_user = await db[USERS].find_one({"_id": staff_oid})
    if not staff_user:
        raise NotFound(message="Staff user not found", code="STAFF_NOT_FOUND")

    updates = {
        "assigned_to": staff_oid,
        "status": TicketStatus.IN_PROGRESS.value if ticket.get("status") == TicketStatus.OPEN.value else ticket.get("status"),
        "updated_at": utcnow(),
    }
    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    # Notify staff member
    await notification_service.create(
        db,
        user_id=staff_oid,
        title="Ticket Assigned to You",
        message=f"Ticket {ticket.get('ticket_number')} has been assigned to you by Administrator.",
        type="ticket_assigned",
        metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number")},
    )

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="ticket_assigned",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number"), "assigned_to": str(staff_oid), "staff_name": staff_user.get("name")},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def reassign_ticket(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    assigned_to: Optional[str] = None,
    department_id: Optional[str] = None,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    if not oid:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    updates: Dict[str, Any] = {"updated_at": utcnow()}
    audit_meta: Dict[str, Any] = {"ticket_number": ticket.get("ticket_number")}

    if department_id:
        dept_oid = to_obj_id(department_id)
        updates["department_id"] = dept_oid
        audit_meta["new_department_id"] = str(dept_oid)

    if assigned_to:
        staff_oid = to_obj_id(assigned_to)
        staff = await db[USERS].find_one({"_id": staff_oid})
        if not staff:
            raise NotFound(message="Assigned staff not found", code="STAFF_NOT_FOUND")
        updates["assigned_to"] = staff_oid
        audit_meta["new_assigned_to"] = str(staff_oid)

        # Notify newly assigned staff
        await notification_service.create(
            db,
            user_id=staff_oid,
            title="Ticket Reassigned to You",
            message=f"Ticket {ticket.get('ticket_number')} has been reassigned to you.",
            type="ticket_assigned",
            metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number")},
        )

    await db[TICKETS].update_one({"_id": oid}, {"$set": updates})

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="ticket_reassigned",
        resource_type="ticket",
        resource_id=oid,
        metadata=audit_meta,
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


async def close_ticket(
    db,
    current_user: Dict[str, Any],
    ticket_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    oid = to_obj_id(ticket_id)
    if not oid:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    ticket = await db[TICKETS].find_one({"_id": oid})
    if not ticket:
        raise NotFound(message="Ticket not found", code="TICKET_NOT_FOUND")

    doc = await db[TICKETS].find_one({"_id": oid})
    if reason:
        add_comment(
            doc,
            user_id=to_obj_id(current_user.get("_id")),
            author_name=current_user.get("name", "Administrator"),
            author_role=UserRole.ADMIN.value,
            text=f"[TICKET CLOSED BY ADMIN]: {reason}",
        )

    updates = {
        "status": TicketStatus.CLOSED.value,
        "resolved_at": ticket.get("resolved_at") or utcnow(),
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
            title="Ticket Closed",
            message=f"Your ticket {ticket.get('ticket_number')} has been closed.",
            type="ticket_closed",
            metadata={"ticket_id": str(oid), "ticket_number": ticket.get("ticket_number")},
        )

    await audit_action(
        db,
        user_id=to_obj_id(current_user.get("_id")),
        action="ticket_closed",
        resource_type="ticket",
        resource_id=oid,
        metadata={"ticket_number": ticket.get("ticket_number"), "reason": reason},
    )

    updated_doc = await db[TICKETS].find_one({"_id": oid})
    return ticket_to_dict(updated_doc)


# ============================================================================
# DOCUMENT INGESTION & TEXT EXTRACTION PIPELINE
# ============================================================================

def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "txt":
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="ignore")

    elif ext == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_text = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages_text).strip()
        except Exception as e:
            raise BadRequest(message=f"Failed to parse PDF document: {e}", code="PDF_PARSE_ERROR")

    elif ext in ("docx", "doc"):
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs).strip()
        except Exception as e:
            raise BadRequest(message=f"Failed to parse DOCX document: {e}", code="DOCX_PARSE_ERROR")

    else:
        raise BadRequest(message=f"Unsupported file format '{ext}'. Allowed: pdf, docx, txt", code="UNSUPPORTED_FORMAT")


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> List[str]:
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


async def process_document_upload(
    db,
    file_bytes: bytes,
    filename: str,
    title: str,
    category: str,
    current_user: Dict[str, Any],
    department_id: Optional[str] = None,
    faculty: Optional[str] = None,
) -> Dict[str, Any]:
    text_content = extract_text_from_file_bytes(file_bytes, filename)
    if not text_content or len(text_content.strip()) < 10:
        raise BadRequest(message="Uploaded document contains insufficient or empty text", code="EMPTY_DOCUMENT")

    user_oid = to_obj_id(current_user.get("_id"))
    dept_oid = to_obj_id(department_id)

    # Chunking & Embeddings
    chunks = chunk_text(text_content)
    embeddings = get_embeddings_provider()

    created_docs = []
    main_doc_id = None

    for idx, chunk in enumerate(chunks):
        chunk_title = f"{title} (Part {idx + 1}/{len(chunks)})" if len(chunks) > 1 else title
        embedding = await embeddings.embed_one(f"{chunk_title}\n\n{chunk}")

        doc = new_knowledge_doc(
            title=chunk_title,
            content=chunk,
            category=category,
            created_by=user_oid,
            department_id=dept_oid,
            faculty=faculty,
            source=filename,
            status=KnowledgeStatus.PUBLISHED.value,
            embedding=embedding,
            metadata={"filename": filename, "chunk_index": idx, "total_chunks": len(chunks)},
        )

        res = await db[KNOWLEDGE_BASE].insert_one(doc)
        if idx == 0:
            main_doc_id = res.inserted_id
        created_docs.append(str(res.inserted_id))

    await audit_action(
        db,
        user_id=user_oid,
        action="knowledge_uploaded",
        resource_type="knowledge",
        resource_id=main_doc_id,
        metadata={"filename": filename, "title": title, "category": category, "chunks_created": len(created_docs)},
    )

    return {
        "title": title,
        "filename": filename,
        "category": category,
        "chunks_count": len(created_docs),
        "document_ids": created_docs,
        "status": KnowledgeStatus.PUBLISHED.value,
        "message": f"Successfully processed and indexed document into {len(created_docs)} knowledge base chunk(s).",
    }

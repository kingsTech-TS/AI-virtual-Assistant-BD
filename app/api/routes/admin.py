#!/usr/bin/env python3
"""
Admin API Router.
Comprehensive management endpoints for administrators and super administrators.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, Header, Path, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.constants.priorities import TicketPriority
from app.constants.roles import UserRole
from app.constants.statuses import FAQStatus, KnowledgeStatus, TicketStatus
from app.database.collections import AUDIT_LOGS, FAQS, KNOWLEDGE_BASE, USERS
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.permissions import require_admin, require_super_admin
from app.models.faq import faq_to_dict, new_faq_doc
from app.schemas.common import MessageResponse, PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.schemas.faq import FAQCreate, FAQResponse, FAQUpdate
from app.schemas.knowledge import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate
from app.schemas.ticket import TicketResponse, TicketUpdate
from app.schemas.user import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
    RoleChangeRequest,
    StaffCreateRequest,
    StaffResponse,
    StaffUpdateRequest,
    UserResponse,
)
from app.services import (
    admin_service,
    analytics_service,
    audit_service,
    department_service,
    faq_service,
    knowledge_service,
    staff_service,
)
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor

router = APIRouter(
    tags=["Admin"],
    dependencies=[Depends(require_admin())],
)


# Request schemas for admin actions
class TicketAssignRequest(BaseModel):
    assigned_to: str = Field(..., description="ID of staff member to assign")


class TicketReassignRequest(BaseModel):
    assigned_to: Optional[str] = Field(None, description="New staff member ID")
    department_id: Optional[str] = Field(None, description="New department ID")


class TicketCloseRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for closing ticket")


# ============================================================================
# 1. ADMIN DASHBOARD
# ============================================================================

@router.get(
    "/dashboard",
    summary="Admin System Dashboard",
    description="Retrieves comprehensive system-wide metrics across users, tickets, chatbot, knowledge, and feedback.",
)
async def get_admin_dashboard(
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    result = await admin_service.get_dashboard(db)
    return {"success": True, "data": result}


# ============================================================================
# 2. USER MANAGEMENT
# ============================================================================

@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    summary="List All Users",
    description="Retrieves a paginated list of all users with optional role and search filters.",
)
async def list_admin_users(
    role: Optional[UserRole] = Query(None),
    search: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    role_val = role.value if hasattr(role, "value") else role
    result = await admin_service.list_users(db, pagination, role=role_val, search=search, department_id=department_id)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get(
    "/users/{user_id}",
    response_model=SuccessResponse[UserResponse],
    summary="Get User By ID",
    description="Retrieves full user details by user ID.",
)
async def get_admin_user(
    user_id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[UserResponse]:
    result = await admin_service.get_user_by_id(db, user_id)
    return SuccessResponse[UserResponse](data=result)


@router.post(
    "/users",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create User (Admin)",
    description="Creates a new student, staff, or admin user. (Only Super Admin can create Super Admin).",
)
async def create_admin_user(
    data: AdminUserCreateRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    result = await admin_service.create_user(db, data, current_user)
    return SuccessResponse[UserResponse](data=result)


@router.patch(
    "/users/{user_id}",
    response_model=SuccessResponse[UserResponse],
    summary="Update User (Admin)",
    description="Updates user profile, role, active status, or department.",
)
async def update_admin_user(
    user_id: str = Path(...),
    data: AdminUserUpdateRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    result = await admin_service.update_user(db, user_id, data, current_user)
    return SuccessResponse[UserResponse](data=result)


@router.delete(
    "/users/{user_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Delete User",
    description="Deletes a user account from the system.",
)
async def delete_admin_user(
    user_id: str = Path(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await admin_service.delete_user(db, user_id, current_user)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/users/{user_id}/role",
    response_model=SuccessResponse[UserResponse],
    summary="Change User Role (Super Admin Only)",
    description="Changes a user's role in the system. Restricted to Super Admin.",
    dependencies=[Depends(require_super_admin())],
)
async def change_user_role(
    user_id: str = Path(...),
    data: RoleChangeRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[UserResponse]:
    role_req = AdminUserUpdateRequest(role=data.role)
    result = await admin_service.update_user(db, user_id, role_req, current_user)
    return SuccessResponse[UserResponse](data=result)


# ============================================================================
# 3. STAFF MANAGEMENT
# ============================================================================

@router.get(
    "/staff",
    response_model=PaginatedResponse[StaffResponse],
    summary="List Staff Members",
    description="Retrieves all staff members with their department and position details.",
)
async def list_admin_staff(
    department_id: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await admin_service.list_users(db, pagination, role=UserRole.STAFF.value, department_id=department_id)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.post(
    "/staff",
    response_model=SuccessResponse[StaffResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Staff Member",
    description="Creates a new staff user with staff ID, position, and department assignment.",
)
async def create_admin_staff(
    data: StaffCreateRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[StaffResponse]:
    user_data = AdminUserCreateRequest(
        name=data.name,
        email=data.email,
        password=data.password,
        role=UserRole.STAFF,
        department_id=data.department_id,
        faculty=data.faculty,
        phone=data.phone,
        staff_id=data.staff_id,
        position=data.position,
        permissions=data.permissions,
    )
    result = await admin_service.create_user(db, user_data, current_user)
    return SuccessResponse[StaffResponse](data=result)


@router.get(
    "/staff/{staff_id}",
    response_model=SuccessResponse[StaffResponse],
    summary="Get Staff Member",
    description="Retrieves staff member details by user ID.",
)
async def get_admin_staff_by_id(
    staff_id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[StaffResponse]:
    result = await admin_service.get_user_by_id(db, staff_id)
    return SuccessResponse[StaffResponse](data=result)


@router.patch(
    "/staff/{staff_id}",
    response_model=SuccessResponse[StaffResponse],
    summary="Update Staff Member",
    description="Updates staff member information, position, department, or permissions.",
)
async def update_admin_staff(
    staff_id: str = Path(...),
    data: StaffUpdateRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[StaffResponse]:
    update_data = AdminUserUpdateRequest(
        name=data.name,
        email=data.email,
        department_id=data.department_id,
        faculty=data.faculty,
        phone=data.phone,
        staff_id=data.staff_id,
        position=data.position,
        permissions=data.permissions,
        is_active=data.is_active,
    )
    result = await admin_service.update_user(db, staff_id, update_data, current_user)
    return SuccessResponse[StaffResponse](data=result)


# ============================================================================
# 4. DEPARTMENT MANAGEMENT
# ============================================================================

@router.get(
    "/departments",
    response_model=PaginatedResponse[DepartmentResponse],
    summary="List Departments",
    description="Retrieves a paginated list of academic departments.",
)
async def list_admin_departments(
    is_active: Optional[bool] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    filters = {"is_active": is_active} if is_active is not None else None
    items, pagination_info = await department_service.list(db, pagination, filters)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "/departments",
    response_model=SuccessResponse[DepartmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Department",
    description="Creates a new academic department.",
)
async def create_admin_department(
    data: DepartmentCreate = Body(...),
    db=Depends(get_db),
) -> SuccessResponse[DepartmentResponse]:
    result = await department_service.create(db, data)
    return SuccessResponse[DepartmentResponse](data=result)


@router.get(
    "/departments/{id}",
    response_model=SuccessResponse[DepartmentResponse],
    summary="Get Department Details",
    description="Retrieves department information by ID.",
)
async def get_admin_department(
    id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[DepartmentResponse]:
    result = await department_service.get(db, id)
    return SuccessResponse[DepartmentResponse](data=result)


@router.patch(
    "/departments/{id}",
    response_model=SuccessResponse[DepartmentResponse],
    summary="Update Department",
    description="Updates department details or active status.",
)
async def update_admin_department(
    id: str = Path(...),
    data: DepartmentUpdate = Body(...),
    db=Depends(get_db),
) -> SuccessResponse[DepartmentResponse]:
    result = await department_service.update(db, id, data)
    return SuccessResponse[DepartmentResponse](data=result)


@router.delete(
    "/departments/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Delete Department",
    description="Deletes an academic department from the system.",
)
async def delete_admin_department(
    id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[Dict[str, Any]]:
    result = await department_service.delete(db, id)
    return SuccessResponse[Dict[str, Any]](data=result)


# ============================================================================
# 5. KNOWLEDGE BASE & DOCUMENT UPLOAD
# ============================================================================

@router.get(
    "/knowledge",
    response_model=PaginatedResponse[Dict[str, Any]],
    summary="List Knowledge Documents (Admin)",
    description="Retrieves all knowledge base entries with status and category filters.",
)
async def list_admin_knowledge(
    category: Optional[str] = Query(None),
    status: Optional[KnowledgeStatus] = Query(None),
    department_id: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    if department_id:
        filters["department_id"] = department_id
    items, pagination_info = await knowledge_service.list(db, pagination, filters or None)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "/knowledge",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    summary="Create Knowledge Document (Admin)",
    description="Creates a new knowledge base entry and generates vector embeddings.",
)
async def create_admin_knowledge(
    data: KnowledgeCreate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.create(db, data, created_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.get(
    "/knowledge/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Knowledge Document Details",
    description="Retrieves knowledge base document by ID.",
)
async def get_admin_knowledge_doc(
    id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.get(db, id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/knowledge/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Update Knowledge Document (Admin)",
    description="Updates a knowledge document and regenerates embedding if content changed.",
)
async def update_admin_knowledge(
    id: str = Path(...),
    data: KnowledgeUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.update(db, id, data, updated_by_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.delete(
    "/knowledge/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Delete Knowledge Document (Admin)",
    description="Deletes a knowledge document from the database.",
)
async def delete_admin_knowledge(
    id: str = Path(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await knowledge_service.delete(db, id, deleter_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


@router.post(
    "/knowledge/upload",
    summary="Upload Academic Document (PDF/DOCX/TXT)",
    description="Uploads a PDF, DOCX, or TXT file, extracts text, splits into chunks, computes embeddings, and stores in the knowledge base.",
)
async def upload_academic_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    department_id: Optional[str] = Form(None),
    faculty: Optional[str] = Form(None),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    file_bytes = await file.read()
    filename = file.filename or "document.txt"
    result = await admin_service.process_document_upload(
        db=db,
        file_bytes=file_bytes,
        filename=filename,
        title=title,
        category=category,
        current_user=current_user,
        department_id=department_id,
        faculty=faculty,
    )
    return {"success": True, "data": result}


# ============================================================================
# 6. FAQ MANAGEMENT
# ============================================================================

@router.get(
    "/faqs",
    response_model=PaginatedResponse[FAQResponse],
    summary="List FAQs (Admin)",
    description="Retrieves a paginated list of FAQs with category and status filters.",
)
async def list_admin_faqs(
    category: Optional[str] = Query(None),
    status: Optional[FAQStatus] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    items, pagination_info = await faq_service.list(db, pagination, filters or None)
    return {
        "success": True,
        "items": items,
        "pagination": pagination_info,
    }


@router.post(
    "/faqs",
    response_model=SuccessResponse[FAQResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create FAQ",
    description="Creates a new FAQ entry.",
)
async def create_admin_faq(
    data: FAQCreate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[FAQResponse]:
    result = await faq_service.create(db, data, created_by_id=current_user.get("_id"))
    return SuccessResponse[FAQResponse](data=result)


@router.patch(
    "/faqs/{id}",
    response_model=SuccessResponse[FAQResponse],
    summary="Update FAQ",
    description="Updates FAQ question, answer, category, or status.",
)
async def update_admin_faq(
    id: str = Path(...),
    data: FAQUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[FAQResponse]:
    result = await faq_service.update(db, id, data, updated_by_id=current_user.get("_id"))
    return SuccessResponse[FAQResponse](data=result)


@router.delete(
    "/faqs/{id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Delete FAQ",
    description="Deletes an FAQ entry.",
)
async def delete_admin_faq(
    id: str = Path(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await faq_service.delete(db, id, deleter_id=current_user.get("_id"))
    return SuccessResponse[Dict[str, Any]](data=result)


# ============================================================================
# 7. TICKET MANAGEMENT (SYSTEM-WIDE)
# ============================================================================

@router.get(
    "/tickets",
    response_model=PaginatedResponse[TicketResponse],
    summary="List All System Tickets",
    description="Retrieves all tickets across all departments with filtering by status, priority, department, and assignee.",
)
async def list_admin_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    department_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    if priority:
        filters["priority"] = priority.value if hasattr(priority, "value") else priority
    if department_id:
        filters["department_id"] = department_id
    if assigned_to:
        filters["assigned_to"] = assigned_to

    result = await admin_service.list_admin_tickets(db, pagination, filters or None)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get(
    "/tickets/{ticket_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Ticket Details (Admin)",
    description="Retrieves complete ticket details including comments and student info.",
)
async def get_admin_ticket_details(
    ticket_id: str = Path(...),
    db=Depends(get_db),
) -> SuccessResponse[Dict[str, Any]]:
    result = await admin_service.get_admin_ticket(db, ticket_id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/tickets/{ticket_id}",
    response_model=SuccessResponse[TicketResponse],
    summary="Update Ticket (Admin)",
    description="Updates ticket status, priority, or category.",
)
async def update_admin_ticket(
    ticket_id: str = Path(...),
    data: TicketUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await staff_service.update_ticket(db, current_user, ticket_id, data)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=SuccessResponse[TicketResponse],
    summary="Assign Ticket to Staff",
    description="Assigns a ticket to a staff member and emits notification.",
)
async def assign_ticket_to_staff(
    ticket_id: str = Path(...),
    data: TicketAssignRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await admin_service.assign_ticket(db, current_user, ticket_id, assigned_to=data.assigned_to)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/reassign",
    response_model=SuccessResponse[TicketResponse],
    summary="Reassign Ticket",
    description="Reassigns a ticket to a different department or staff member.",
)
async def reassign_ticket_admin(
    ticket_id: str = Path(...),
    data: TicketReassignRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await admin_service.reassign_ticket(
        db,
        current_user,
        ticket_id,
        assigned_to=data.assigned_to,
        department_id=data.department_id,
    )
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/close",
    response_model=SuccessResponse[TicketResponse],
    summary="Close Ticket (Admin)",
    description="Closes a ticket and records administrative closing reason.",
)
async def close_ticket_admin(
    ticket_id: str = Path(...),
    data: TicketCloseRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await admin_service.close_ticket(db, current_user, ticket_id, reason=data.reason)
    return SuccessResponse[TicketResponse](data=result)


# ============================================================================
# 8. ANALYTICS (ADMIN)
# ============================================================================

@router.get(
    "/analytics/overview",
    summary="Analytics Overview",
    description="Retrieves overall institutional metrics and KPI indicators.",
)
async def admin_analytics_overview(
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await analytics_service.overview(db)
    return {"success": True, "data": result}


@router.get(
    "/analytics/tickets",
    summary="Ticket Analytics",
    description="Ticket volume trends, resolution rates, and departmental breakdown.",
)
async def admin_analytics_tickets(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await analytics_service.tickets(db, days=days)
    return {"success": True, "data": result}


@router.get(
    "/analytics/intents",
    summary="Intent Distribution Analytics",
    description="Intent recognition frequency and AI confidence distribution.",
)
async def admin_analytics_intents(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await analytics_service.intents(db, days=days)
    return {"success": True, "data": result}


@router.get(
    "/analytics/feedback",
    summary="Feedback Analytics",
    description="Student satisfaction breakdown and recent feedback comments.",
)
async def admin_analytics_feedback(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await analytics_service.feedback(db, days=days)
    return {"success": True, "data": result}


@router.get(
    "/analytics/knowledge",
    summary="Knowledge Base Analytics",
    description="Document counts, category distribution, and coverage metrics.",
)
async def admin_analytics_knowledge(
    db=Depends(get_db),
) -> Dict[str, Any]:
    result = await analytics_service.knowledge(db)
    return {"success": True, "data": result}


# ============================================================================
# 9. AUDIT LOGS
# ============================================================================

@router.get(
    "/audit-logs",
    summary="List System Audit Logs",
    description="Retrieves immutable system audit logs tracking administrative actions.",
)
async def list_audit_logs(
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
) -> Dict[str, Any]:
    query: Dict[str, Any] = {}
    if action:
        query["action"] = action
    if user_id:
        user_oid = to_obj_id(user_id)
        if user_oid:
            query["user_id"] = user_oid
    if date_from or date_to:
        created_at_filter: Dict[str, Any] = {}
        if date_from:
            created_at_filter["$gte"] = date_from
        if date_to:
            created_at_filter["$lte"] = date_to
        query["created_at"] = created_at_filter

    items, pagination_info = await paginate_cursor(
        db[AUDIT_LOGS],
        query,
        page=pagination.page,
        limit=pagination.limit,
        sort=[("created_at", -1)],
    )

    normalized_items = []
    for item in items:
        normalized = dict(item)
        if "_id" in normalized:
            normalized["_id"] = str(normalized["_id"])
        if "user_id" in normalized and normalized["user_id"]:
            normalized["user_id"] = str(normalized["user_id"])
        if "resource_id" in normalized and normalized["resource_id"]:
            normalized["resource_id"] = str(normalized["resource_id"])
        normalized_items.append(normalized)

    return {"success": True, "items": normalized_items, "pagination": pagination_info}

#!/usr/bin/env python3
"""
Staff API Router.
Endpoints for Staff dashboard, ticket response, assignment, escalation, and resolution.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, status
from pydantic import BaseModel, Field

from app.constants.priorities import TicketPriority
from app.constants.roles import UserRole
from app.constants.statuses import TicketStatus
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.permissions import require_staff
from app.schemas.common import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.ticket import TicketResponse, TicketUpdate
from app.services import staff_service

router = APIRouter(
    tags=["Staff"],
    dependencies=[Depends(require_staff())],
)


class StaffRespondRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Response message for the student")


class StaffEscalateRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)
    priority: TicketPriority = TicketPriority.URGENT


class StaffResolveRequest(BaseModel):
    resolution_note: Optional[str] = Field(None, max_length=2000)


@router.get(
    "/dashboard",
    summary="Staff Dashboard Statistics",
    description="Retrieves ticket counts, triage statistics, and recent activity for the staff dashboard.",
)
async def get_staff_dashboard(
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    result = await staff_service.get_dashboard(db, current_user)
    return {"success": True, "data": result}


@router.get(
    "/tickets",
    response_model=PaginatedResponse[TicketResponse],
    summary="List Staff Tickets",
    description="Retrieves tickets assigned to staff or belonging to their department.",
)
async def list_staff_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    assigned_only: Optional[bool] = Query(None),
    pagination: PaginationParams = Depends(),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if status:
        filters["status"] = status.value if hasattr(status, "value") else status
    if priority:
        filters["priority"] = priority.value if hasattr(priority, "value") else priority
    if assigned_only:
        filters["assigned_only"] = True

    result = await staff_service.list_tickets(db, current_user, pagination, filters or None)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get(
    "/tickets/{ticket_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    summary="Get Staff Ticket Details",
    description="Retrieves full ticket details including student info (strictly scoped to staff's department or assignments).",
)
async def get_staff_ticket(
    ticket_id: str = Path(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[Dict[str, Any]]:
    result = await staff_service.get_ticket(db, current_user, ticket_id)
    return SuccessResponse[Dict[str, Any]](data=result)


@router.patch(
    "/tickets/{ticket_id}",
    response_model=SuccessResponse[TicketResponse],
    summary="Update Staff Ticket",
    description="Updates ticket status, priority, or category.",
)
async def update_staff_ticket(
    ticket_id: str = Path(...),
    data: TicketUpdate = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await staff_service.update_ticket(db, current_user, ticket_id, data)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/respond",
    response_model=SuccessResponse[TicketResponse],
    summary="Respond to Student Ticket",
    description="Appends a response to the ticket, sets status to waiting_for_student, and notifies the student.",
)
async def respond_staff_ticket(
    ticket_id: str = Path(...),
    data: StaffRespondRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await staff_service.respond(db, current_user, ticket_id, message=data.message)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=SuccessResponse[TicketResponse],
    summary="Assign Ticket to Self",
    description="Assigns the ticket to the currently logged in staff member.",
)
async def assign_staff_ticket(
    ticket_id: str = Path(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await staff_service.assign_to_self(db, current_user, ticket_id)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/escalate",
    response_model=SuccessResponse[TicketResponse],
    summary="Escalate Ticket",
    description="Escalates ticket priority and appends an escalation notice.",
)
async def escalate_staff_ticket(
    ticket_id: str = Path(...),
    data: StaffEscalateRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    priority_val = data.priority.value if hasattr(data.priority, "value") else data.priority
    result = await staff_service.escalate(db, current_user, ticket_id, reason=data.reason, priority=priority_val)
    return SuccessResponse[TicketResponse](data=result)


@router.post(
    "/tickets/{ticket_id}/resolve",
    response_model=SuccessResponse[TicketResponse],
    summary="Resolve Ticket",
    description="Marks ticket as resolved, optionally records a resolution note, and notifies the student.",
)
async def resolve_staff_ticket(
    ticket_id: str = Path(...),
    data: StaffResolveRequest = Body(...),
    db=Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await staff_service.resolve(db, current_user, ticket_id, resolution_note=data.resolution_note)
    return SuccessResponse[TicketResponse](data=result)

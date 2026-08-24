from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status

from app.constants.priorities import TicketPriority
from app.constants.statuses import TicketStatus
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.schemas.common import PaginatedResponse, PaginationParams, SuccessResponse
from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate
from app.services import ticket_service

router = APIRouter(tags=["Tickets"])


@router.post(
    "",
    response_model=SuccessResponse[TicketResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Support Ticket",
    description="Creates a new support ticket and emits notification to relevant staff.",
)
async def create_ticket(
    data: TicketCreate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await ticket_service.create(db, current_user, data)
    return SuccessResponse[TicketResponse](data=result)


@router.get(
    "",
    response_model=PaginatedResponse[TicketResponse],
    summary="List Support Tickets",
    description="Retrieves a paginated list of tickets scoped by user role.",
)
async def list_tickets(
    status: Optional[TicketStatus] = Query(None),
    priority: Optional[TicketPriority] = Query(None),
    department_id: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
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

    result = await ticket_service.list(db, current_user, pagination, filters or None)
    return {
        "success": True,
        "items": result["items"],
        "pagination": result["pagination"],
    }


@router.get(
    "/{ticket_id}",
    response_model=SuccessResponse[TicketResponse],
    summary="Get Support Ticket by ID",
    description="Retrieves ticket details with permission verification.",
)
async def get_ticket(
    ticket_id: str,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await ticket_service.get(db, current_user, ticket_id)
    return SuccessResponse[TicketResponse](data=result)


@router.patch(
    "/{ticket_id}",
    response_model=SuccessResponse[TicketResponse],
    summary="Update Support Ticket",
    description="Updates ticket status, priority, assignment, or appends a comment.",
)
async def update_ticket(
    ticket_id: str,
    data: TicketUpdate,
    db: Any = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SuccessResponse[TicketResponse]:
    result = await ticket_service.update(db, current_user, ticket_id, data)
    return SuccessResponse[TicketResponse](data=result)

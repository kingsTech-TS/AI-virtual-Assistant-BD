from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.constants.roles import UserRole
from app.dependencies.auth import require_roles
from app.dependencies.database import get_db
from app.schemas.common import SuccessResponse
from app.services import analytics_service

router = APIRouter(
    tags=["Analytics"],
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)


@router.get(
    "/overview",
    summary="Analytics Overview",
    description="Retrieves high-level counts and statistics (students, conversations, tickets, feedback).",
)
async def analytics_overview(
    db=Depends(get_db),
):
    result = await analytics_service.overview(db)
    return {"success": True, "data": result}


@router.get(
    "/intents",
    summary="Intent Distribution Analytics",
    description="Retrieves distribution and confidence metrics of detected intents.",
)
async def analytics_intents(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
):
    items = await analytics_service.intents(db, days=days)
    return {"success": True, "data": items}


@router.get(
    "/tickets",
    summary="Ticket Metrics Analytics",
    description="Retrieves ticket breakdown by status, priority, department, and resolution time.",
)
async def analytics_tickets(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
):
    result = await analytics_service.tickets(db, days=days)
    return {"success": True, "data": result}


@router.get(
    "/feedback",
    summary="Feedback Analytics",
    description="Retrieves breakdown of positive/negative feedback, ratings per day, and recent comments.",
)
async def analytics_feedback(
    days: int = Query(30, ge=1, le=365),
    db=Depends(get_db),
):
    result = await analytics_service.feedback(db, days=days)
    return {"success": True, "data": result}

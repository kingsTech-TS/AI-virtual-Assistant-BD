from typing import Any, Dict

from fastapi import APIRouter

from app.database.mongodb import db_manager

router = APIRouter(tags=["Health"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    db_status = await db_manager.health_check()
    overall_status = "healthy" if db_status["status"] == "connected" else "unhealthy"
    return {
        "success": True,
        "data": {
            "status": overall_status,
            "database": db_status["status"],
        },
    }


@router.get("/database")
async def database_health_detail() -> Dict[str, Any]:
    db_status = await db_manager.health_check()
    return {
        "success": True,
        "data": {
            "database": db_status,
        },
    }

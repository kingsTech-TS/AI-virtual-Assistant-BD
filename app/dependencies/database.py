from __future__ import annotations

from typing import Any, Dict, Optional

from app.database.mongodb import db_manager


async def get_db():
    return db_manager.get_database()

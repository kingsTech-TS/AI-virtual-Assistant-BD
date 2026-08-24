from __future__ import annotations

from typing import Any, Dict, Optional

from app.database.collections import AUDIT_LOGS
from app.models.audit_log import new_audit_log_doc


async def audit_action(
    db,
    user_id=None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id=None,
    metadata: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> str:
    doc = new_audit_log_doc(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        ip=ip,
        user_agent=ua,
    )
    result = await db[AUDIT_LOGS].insert_one(doc)
    return str(result.inserted_id)

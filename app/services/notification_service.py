from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.exceptions import NotFound
from app.database.collections import NOTIFICATIONS
from app.models.notification import new_notification_doc, notification_to_dict
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id
from app.utils.pagination import paginate_cursor


async def create(
    db,
    user_id,
    title: str,
    message: str,
    type: str = "general",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    doc = new_notification_doc(
        user_id=to_obj_id(user_id),
        title=title,
        message=message,
        type=type,
        metadata=metadata,
    )
    result = await db[NOTIFICATIONS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return notification_to_dict(doc)


async def list_for_user(
    db,
    user_id,
    pagination_params,
    only_unread: bool = False,
) -> Dict[str, Any]:
    query: Dict[str, Any] = {"user_id": to_obj_id(user_id)}
    if only_unread:
        query["is_read"] = False
    items, pagination = await paginate_cursor(
        db[NOTIFICATIONS],
        query,
        page=pagination_params.page,
        limit=pagination_params.limit,
        sort=[("created_at", -1)],
    )
    items_dicts = [notification_to_dict(item) for item in items]
    return {"items": items_dicts, "pagination": pagination}


async def mark_read(
    db,
    user_id,
    notification_id,
) -> Dict[str, Any]:
    oid = to_obj_id(notification_id)
    user_oid = to_obj_id(user_id)
    result = await db[NOTIFICATIONS].find_one_and_update(
        {"_id": oid, "user_id": user_oid},
        {"$set": {"is_read": True}},
        return_document=True,
    )
    if not result:
        raise NotFound(message="Notification not found")
    return notification_to_dict(result)

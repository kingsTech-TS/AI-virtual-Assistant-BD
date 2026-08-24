import math
from typing import Any, Dict, List, Tuple, Union

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor
from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    limit: int = Field(..., ge=1, description="Items per page")
    total: int = Field(..., ge=0, description="Total matching items")
    pages: int = Field(..., ge=0, description="Total number of pages")


def _normalize_limit(limit: int, max_limit: int) -> int:
    if limit <= 0:
        return 10
    return min(limit, max_limit)


def _normalize_page(page: int) -> int:
    return max(page, 1)


async def paginate_cursor(
    collection_or_cursor: Union[AsyncIOMotorCollection, AsyncIOMotorCursor],
    query: Dict[str, Any],
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100,
    sort: List[Tuple[str, int]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    normalized_limit = _normalize_limit(limit, max_limit)
    normalized_page = _normalize_page(page)
    skip = (normalized_page - 1) * normalized_limit

    effective_sort = sort if sort is not None else [("created_at", -1)]

    cursor: AsyncIOMotorCursor
    if isinstance(collection_or_cursor, AsyncIOMotorCursor):
        cursor = collection_or_cursor
        total = await cursor.clone().count() if hasattr(cursor, "clone") else 0
    else:
        cursor = collection_or_cursor.find(query)
        total = await collection_or_cursor.count_documents(query)

    if sort is not None and isinstance(collection_or_cursor, AsyncIOMotorCollection):
        cursor = cursor.sort(effective_sort)

    cursor = cursor.skip(skip).limit(normalized_limit)
    items: List[Dict[str, Any]] = await cursor.to_list(length=normalized_limit)

    total_pages = math.ceil(total / normalized_limit) if normalized_limit > 0 else 0

    pagination: Dict[str, Any] = {
        "page": normalized_page,
        "limit": normalized_limit,
        "total": total,
        "pages": total_pages,
    }

    return items, pagination

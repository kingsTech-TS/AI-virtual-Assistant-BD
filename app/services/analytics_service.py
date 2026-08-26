from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from app.constants.roles import UserRole
from app.constants.statuses import TicketStatus, KnowledgeStatus
from app.database.collections import USERS, CONVERSATIONS, MESSAGES, TICKETS, DEPARTMENTS, FEEDBACK, KNOWLEDGE_BASE
from app.models.feedback import RATING_POSITIVE, RATING_NEGATIVE
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id


async def overview(db) -> Dict[str, Any]:
    total_students = await db[USERS].count_documents({"role": UserRole.STUDENT.value})
    total_conversations = await db[CONVERSATIONS].count_documents({})
    total_messages = await db[MESSAGES].count_documents({})
    total_tickets = await db[TICKETS].count_documents({})
    open_tickets = await db[TICKETS].count_documents({"status": TicketStatus.OPEN.value})
    resolved_tickets = await db[TICKETS].count_documents({
        "status": {"$in": [TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]}
    })
    unanswered_count = await db[TICKETS].count_documents({
        "status": {"$in": [
            TicketStatus.OPEN.value,
            TicketStatus.IN_PROGRESS.value,
            TicketStatus.WAITING_FOR_STUDENT.value,
        ]}
    })

    feedback_pipeline = [
        {
            "$group": {
                "_id": None,
                "total_positive": {"$sum": {"$cond": [{"$eq": ["$rating", RATING_POSITIVE]}, 1, 0]}},
                "total_negative": {"$sum": {"$cond": [{"$eq": ["$rating", RATING_NEGATIVE]}, 1, 0]}},
                "total": {"$sum": 1},
            }
        }
    ]
    feedback_result = await db[FEEDBACK].aggregate(feedback_pipeline).to_list(length=1)
    avg_feedback_rating = 0.0
    if feedback_result and feedback_result[0].get("total", 0) > 0:
        row = feedback_result[0]
        avg_feedback_rating = row.get("total_positive", 0) / row["total"]

    return {
        "total_students": total_students,
        "total_conversations": total_conversations,
        "total_messages": total_messages,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "resolved_tickets": resolved_tickets,
        "avg_feedback_rating": avg_feedback_rating,
        "unanswered_count": unanswered_count,
    }


async def intents(db, days: int = 30) -> List[Dict[str, Any]]:
    cutoff = utcnow() - timedelta(days=days)
    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": cutoff},
                "intent": {"$exists": True, "$ne": None},
            }
        },
        {
            "$group": {
                "_id": "$intent",
                "count": {"$sum": 1},
                "avg_confidence": {"$avg": "$confidence"},
            }
        },
        {
            "$sort": {"count": -1}
        },
        {
            "$limit": 15
        },
        {
            "$project": {
                "_id": 0,
                "intent": "$_id",
                "count": 1,
                "avg_confidence": 1,
            }
        }
    ]
    results = await db[MESSAGES].aggregate(pipeline).to_list(length=15)
    return results


async def tickets(db, days: int = 30) -> Dict[str, Any]:
    cutoff = utcnow() - timedelta(days=days)

    status_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    status_results = await db[TICKETS].aggregate(status_pipeline).to_list(length=None)
    by_status: Dict[str, int] = {s.value: 0 for s in TicketStatus}
    for row in status_results:
        by_status[row["_id"]] = row["count"]

    priority_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}},
    ]
    priority_results = await db[TICKETS].aggregate(priority_pipeline).to_list(length=None)
    by_priority: Dict[str, int] = {}
    for row in priority_results:
        by_priority[row["_id"]] = row["count"]

    dept_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {
            "$lookup": {
                "from": DEPARTMENTS,
                "localField": "department_id",
                "foreignField": "_id",
                "as": "dept_info",
            }
        },
        {"$unwind": {"path": "$dept_info", "preserveNullAndEmptyArrays": True}},
        {
            "$group": {
                "_id": "$department_id",
                "name": {"$first": "$dept_info.name"},
                "code": {"$first": "$dept_info.code"},
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": {"$ifNull": ["$name", "Unknown"]},
                "code": {"$ifNull": ["$code", "N/A"]},
                "count": 1,
            }
        },
        {"$sort": {"count": -1}},
    ]
    by_department = await db[TICKETS].aggregate(dept_pipeline).to_list(length=None)

    resolution_pipeline = [
        {
            "$match": {
                "created_at": {"$gte": cutoff},
                "resolved_at": {"$exists": True, "$ne": None},
            }
        },
        {
            "$project": {
                "duration_ms": {"$subtract": ["$resolved_at", "$created_at"]}
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_ms": {"$avg": "$duration_ms"}
            }
        },
    ]
    resolution_results = await db[TICKETS].aggregate(resolution_pipeline).to_list(length=1)
    resolution_time_avg_minutes = 0.0
    if resolution_results:
        avg_ms = resolution_results[0].get("avg_ms", 0)
        if avg_ms:
            resolution_time_avg_minutes = avg_ms / 60000.0

    return {
        "by_status": by_status,
        "by_priority": by_priority,
        "by_department": by_department,
        "resolution_time_avg_minutes": resolution_time_avg_minutes,
    }


async def feedback(db, days: int = 30) -> Dict[str, Any]:
    cutoff = utcnow() - timedelta(days=days)

    count_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {
            "$group": {
                "_id": None,
                "total_positive": {"$sum": {"$cond": [{"$eq": ["$rating", RATING_POSITIVE]}, 1, 0]}},
                "total_negative": {"$sum": {"$cond": [{"$eq": ["$rating", RATING_NEGATIVE]}, 1, 0]}},
                "total_count": {"$sum": 1},
            }
        },
    ]
    count_results = await db[FEEDBACK].aggregate(count_pipeline).to_list(length=1)
    total_positive = 0
    total_negative = 0
    total_count = 0
    if count_results:
        total_positive = count_results[0].get("total_positive", 0)
        total_negative = count_results[0].get("total_negative", 0)
        total_count = count_results[0].get("total_count", 0)

    per_day_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {
            "$project": {
                "date": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                }
            }
        },
        {"$group": {"_id": "$date", "count": {"$sum": 1}}},
        {"$group": {"_id": None, "avg_per_day": {"$avg": "$count"}}},
    ]
    per_day_results = await db[FEEDBACK].aggregate(per_day_pipeline).to_list(length=1)
    avg_per_day = 0.0
    if per_day_results:
        avg_per_day = per_day_results[0].get("avg_per_day", 0.0)

    comments_cursor = db[FEEDBACK].find(
        {"created_at": {"$gte": cutoff}, "comment": {"$exists": True, "$ne": None}},
        {"rating": 1, "comment": 1, "created_at": 1, "user_id": 1},
    ).sort("created_at", -1).limit(10)
    recent_comments_docs = await comments_cursor.to_list(length=10)
    recent_comments: List[Dict[str, Any]] = []
    for doc in recent_comments_docs:
        recent_comments.append({
            "rating": doc.get("rating"),
            "comment": doc.get("comment"),
            "created_at": doc.get("created_at"),
            "user_id": str(doc["user_id"]) if doc.get("user_id") else None,
        })

    return {
        "total_positive": total_positive,
        "total_negative": total_negative,
        "total_count": total_count,
        "avg_per_day": avg_per_day,
        "recent_comments": recent_comments,
    }


async def knowledge(db) -> Dict[str, Any]:
    total_docs = await db[KNOWLEDGE_BASE].count_documents({})
    published = await db[KNOWLEDGE_BASE].count_documents({"status": KnowledgeStatus.PUBLISHED.value})
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    by_category = await db[KNOWLEDGE_BASE].aggregate(pipeline).to_list(length=50)
    category_breakdown = {item["_id"]: item["count"] for item in by_category if item["_id"]}

    return {
        "total_documents": total_docs,
        "published_documents": published,
        "by_category": category_breakdown,
    }

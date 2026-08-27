from typing import List

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.database import Database

USERS: str = "users"
CONVERSATIONS: str = "conversations"
MESSAGES: str = "messages"
KNOWLEDGE_BASE: str = "knowledge_base"
FAQS: str = "faqs"
TICKETS: str = "tickets"
DEPARTMENTS: str = "departments"
NOTIFICATIONS: str = "notifications"
FEEDBACK: str = "feedback"
AUDIT_LOGS: str = "audit_logs"
PASSWORD_RESET_TOKENS: str = "password_reset_tokens"

ALL_COLLECTIONS: List[str] = [
    USERS,
    CONVERSATIONS,
    MESSAGES,
    KNOWLEDGE_BASE,
    FAQS,
    TICKETS,
    DEPARTMENTS,
    NOTIFICATIONS,
    FEEDBACK,
    AUDIT_LOGS,
    PASSWORD_RESET_TOKENS,
]


def get_collection(db: Database, name: str) -> AsyncIOMotorCollection:
    if name not in ALL_COLLECTIONS:
        raise ValueError(f"Unknown collection: {name}")
    return db[name]

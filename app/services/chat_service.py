from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.ai.guardrails import apply_guardrails
from app.ai.intent_classifier import get_intent_classifier
from app.ai.rag_service import get_rag_service
from app.ai.response_generator import get_response_generator
from app.constants.intents import INTENT_TO_CATEGORY
from app.database.collections import CONVERSATIONS, MESSAGES
from app.dependencies.permissions import ensure_conversation_owner_or_admin
from app.models.message import (
    MESSAGE_SENDER_ASSISTANT,
    MESSAGE_SENDER_STUDENT,
    message_to_dict,
    new_message_doc,
)
from app.schemas.chat import ChatRequest, ChatResponseData, SourceInfo
from app.services.conversation_service import create_conversation
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id


# --- Idempotency / double-submit protection -------------------------------
# Browsers double-fire requests (React StrictMode in dev, double-clicks, retries
# on a slow network). Without a guard each fire persists its own student +
# assistant pair, so a conversation ends up with duplicated turns. We (a)
# serialize a single user's chat requests with an in-process lock so two
# concurrent fires can't race, and (b) treat an identical message that arrived
# within a short window as a duplicate — returning the reply already generated
# for it instead of calling the gateway again. This both removes the duplicate
# and avoids a wasted (rate-limited) LLM call.
_DEDUP_WINDOW_SECONDS = 15

_user_locks: Dict[str, asyncio.Lock] = {}
_user_locks_guard = asyncio.Lock()


async def _get_user_lock(user_key: str) -> asyncio.Lock:
    async with _user_locks_guard:
        lock = _user_locks.get(user_key)
        if lock is None:
            lock = asyncio.Lock()
            _user_locks[user_key] = lock
        return lock


async def _find_duplicate_reply(db, conv_id, content: str, cutoff) -> Optional[Dict[str, Any]]:
    """Return the assistant reply for a recent identical student message in this
    conversation, or None. Used to make a double-fired request idempotent."""
    dup_student = await db[MESSAGES].find_one(
        {
            "conversation_id": conv_id,
            "sender": MESSAGE_SENDER_STUDENT,
            "content": content,
            "created_at": {"$gte": cutoff},
        },
        sort=[("created_at", -1)],
    )
    if not dup_student:
        return None
    return await db[MESSAGES].find_one(
        {
            "conversation_id": conv_id,
            "sender": MESSAGE_SENDER_ASSISTANT,
            "created_at": {"$gte": dup_student.get("created_at")},
        },
        sort=[("created_at", 1)],
    )


def _reply_doc_to_response(conv_id, assistant: Dict[str, Any]) -> ChatResponseData:
    stored_sources = assistant.get("sources") or []
    response_sources = [
        SourceInfo(id=s.get("id"), title=s.get("title"), category=s.get("category"))
        for s in stored_sources
    ]
    return ChatResponseData(
        conversation_id=str(conv_id),
        message_id=str(assistant.get("_id")),
        response=assistant.get("content", ""),
        intent=assistant.get("intent"),
        confidence=assistant.get("confidence"),
        sources=response_sources,
        requires_human_support=bool(assistant.get("requires_human_support", False)),
    )


async def process_chat(
    db,
    current_user: Dict[str, Any],
    req: ChatRequest,
) -> ChatResponseData:
    user_oid = to_obj_id(current_user.get("_id"))

    # Anchor the duplicate window to when the request ARRIVED, before we block
    # on the lock. The first of two double-fired requests may take up to the
    # full LLM timeout; anchoring here (rather than after acquiring the lock)
    # guarantees the queued duplicate still sees the first request's messages
    # inside its window no matter how slow that first request was.
    arrival = utcnow()

    # Serialize this user's chat requests so a double-fire can't create two
    # message pairs by racing the duplicate check below.
    lock = await _get_user_lock(str(user_oid))
    async with lock:
        return await _process_chat_locked(db, current_user, req, user_oid, arrival)


async def _process_chat_locked(
    db,
    current_user: Dict[str, Any],
    req: ChatRequest,
    user_oid: Any,
    arrival,
) -> ChatResponseData:
    department_id = current_user.get("department_id")
    cutoff = arrival - timedelta(seconds=_DEDUP_WINDOW_SECONDS)

    if req.conversation_id is None:
        # A double-fired *first* message would otherwise create two separate
        # conversations. If this user just started one with the same text,
        # reuse its reply instead.
        recent_conv = await db[CONVERSATIONS].find_one(
            {"user_id": user_oid, "updated_at": {"$gte": cutoff}},
            sort=[("updated_at", -1)],
        )
        if recent_conv is not None:
            dup_reply = await _find_duplicate_reply(db, recent_conv["_id"], req.message, cutoff)
            if dup_reply is not None:
                return _reply_doc_to_response(recent_conv["_id"], dup_reply)
        conv = await create_conversation(db, user_oid, req.message)
        conv_id = to_obj_id(conv.get("_id"))
        is_first_message = True
    else:
        conv = await ensure_conversation_owner_or_admin(db, req.conversation_id, current_user)
        conv_id = to_obj_id(conv.get("_id"))
        dup_reply = await _find_duplicate_reply(db, conv_id, req.message, cutoff)
        if dup_reply is not None:
            return _reply_doc_to_response(conv_id, dup_reply)
        existing_msgs = await db[MESSAGES].count_documents({"conversation_id": conv_id})
        is_first_message = existing_msgs == 0

    student_msg = new_message_doc(
        conversation_id=conv_id,
        sender=MESSAGE_SENDER_STUDENT,
        content=req.message,
    )
    student_result = await db[MESSAGES].insert_one(student_msg)
    student_msg["_id"] = student_result.inserted_id

    intent_classifier = get_intent_classifier()
    classification = await intent_classifier.classify(req.message)
    intent = classification.get("intent")
    confidence = classification.get("confidence", 0.0)

    rag_service = get_rag_service()
    category_filter = INTENT_TO_CATEGORY.get(intent) if intent else None
    sources = await rag_service.retrieve(
        db,
        req.message,
        category_filter=category_filter,
        department_id=department_id,
        top_k=5,
    )

    response_generator = get_response_generator()
    gen_result = await response_generator.generate(req.message, intent, confidence, sources)
    raw_response = gen_result.get("response", "")
    gen_requires_human = gen_result.get("requires_human_support", False)

    guardrail_result = apply_guardrails(req.message, raw_response, sources, confidence, intent)
    final_response = guardrail_result.get("response", raw_response)
    guardrail_requires_human = guardrail_result.get("requires_human_support", False)
    requires_human_support = gen_requires_human or guardrail_requires_human

    storage_sources: List[Dict[str, Any]] = []
    for s in sources:
        storage_sources.append({
            "id": s.get("id"),
            "title": s.get("title"),
            "category": s.get("category"),
        })

    assistant_msg = new_message_doc(
        conversation_id=conv_id,
        sender=MESSAGE_SENDER_ASSISTANT,
        content=final_response,
        intent=intent,
        confidence=confidence,
        sources=storage_sources,
        requires_human_support=requires_human_support,
    )
    assistant_result = await db[MESSAGES].insert_one(assistant_msg)
    assistant_msg["_id"] = assistant_result.inserted_id

    conv_update: Dict[str, Any] = {"updated_at": utcnow()}
    if is_first_message:
        title = req.message[:50].strip() or "New Conversation"
        conv_update["title"] = title
    await db[CONVERSATIONS].update_one({"_id": conv_id}, {"$set": conv_update})

    response_sources: List[SourceInfo] = []
    for s in storage_sources:
        response_sources.append(SourceInfo(
            id=s.get("id"),
            title=s.get("title"),
            category=s.get("category"),
        ))

    return ChatResponseData(
        conversation_id=str(conv_id),
        message_id=str(assistant_result.inserted_id),
        response=final_response,
        intent=intent,
        confidence=confidence,
        sources=response_sources,
        requires_human_support=requires_human_support,
    )

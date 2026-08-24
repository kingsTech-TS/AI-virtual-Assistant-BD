from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.database.collections import CONVERSATIONS, DEPARTMENTS, MESSAGES
from app.dependencies.permissions import ensure_conversation_owner_or_admin
from app.models.message import (
    MESSAGE_SENDER_ASSISTANT,
    MESSAGE_SENDER_STUDENT,
    new_message_doc,
)
from app.schemas.chat import ChatRequest, ChatResponseData, SourceInfo
from app.services.conversation_service import create_conversation
from app.services.escalation_service import get_escalation_service
from app.services.intent_service import get_intent_service
from app.services.llm_service import get_llm_service
from app.services.retrieval_service import get_retrieval_service
from app.utils.ids import to_obj_id

_DEDUP_WINDOW_SECONDS = 30

_user_locks: Dict[str, asyncio.Lock] = {}
_user_locks_guard = asyncio.Lock()


async def _get_user_lock(user_key: str) -> asyncio.Lock:
    async with _user_locks_guard:
        lock = _user_locks.get(user_key)
        if lock is None:
            lock = asyncio.Lock()
            _user_locks[user_key] = lock
        return lock


async def _find_duplicate_reply(db, conv_id, content: str, cutoff: datetime) -> Optional[Dict[str, Any]]:
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
        SourceInfo(
            id=s.get("id"),
            document_id=s.get("document_id") or s.get("id"),
            title=s.get("title"),
            section=s.get("section"),
            page=s.get("page"),
            category=s.get("category"),
        )
        for s in stored_sources
    ]
    resp_text = assistant.get("content", "")
    req_human = bool(assistant.get("requires_human_support", False) or assistant.get("requires_human", False))
    return ChatResponseData(
        conversation_id=str(conv_id),
        message_id=str(assistant.get("_id")),
        response=resp_text,
        message=resp_text,
        intent=assistant.get("intent"),
        confidence=assistant.get("confidence"),
        sources=response_sources,
        requires_human_support=req_human,
        requires_human=req_human,
    )


async def process_chat(
    db,
    current_user: Dict[str, Any],
    req: ChatRequest,
) -> ChatResponseData:
    user_oid = to_obj_id(current_user.get("_id"))
    arrival = datetime.utcnow()

    lock = await _get_user_lock(str(user_oid))
    async with lock:
        return await _process_chat_locked(db, current_user, req, user_oid, arrival)


async def _process_chat_locked(
    db,
    current_user: Dict[str, Any],
    req: ChatRequest,
    user_oid: Any,
    arrival: datetime,
) -> ChatResponseData:
    department_id = current_user.get("department_id")
    cutoff = arrival - timedelta(seconds=_DEDUP_WINDOW_SECONDS)

    # 1. Resolve or create conversation with dedup protection
    if req.conversation_id is None:
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

    # 2. Record incoming student message
    student_msg = new_message_doc(
        conversation_id=conv_id,
        sender=MESSAGE_SENDER_STUDENT,
        content=req.message,
    )
    student_result = await db[MESSAGES].insert_one(student_msg)
    student_msg["_id"] = student_result.inserted_id

    # 3. Pull recent conversation history for memory
    history_cursor = db[MESSAGES].find(
        {"conversation_id": conv_id, "_id": {"$ne": student_result.inserted_id}}
    ).sort("created_at", -1).limit(6)
    history_docs = await history_cursor.to_list(length=6)
    history_docs.reverse()

    # 4. Assemble trusted student profile context
    student_context: Dict[str, Any] = {}
    if current_user.get("matric_number"):
        student_context["matric_number"] = current_user.get("matric_number")
    if current_user.get("level"):
        student_context["level"] = current_user.get("level")
    if department_id:
        dept_doc = await db[DEPARTMENTS].find_one({"_id": to_obj_id(department_id)})
        if dept_doc:
            student_context["department_name"] = dept_doc.get("name")

    # 5. Intent Classification
    intent_service = get_intent_service()
    classification = await intent_service.classify(req.message)
    intent = classification.intent
    category = classification.category
    confidence = classification.confidence
    immediate_human = classification.requires_human

    # 6. Knowledge Base Retrieval (Hybrid Vector Search + Exact Entity + Reranking)
    retrieval_service = get_retrieval_service()
    sources, top_score, meets_threshold = await retrieval_service.retrieve(
        db=db,
        question=req.message,
        intent=intent,
        category=category,
        department_id=department_id,
        top_k=4,
    )

    # 7. Escalation Check
    escalation_service = get_escalation_service()
    should_escalate, _ = escalation_service.should_escalate(
        question=req.message,
        intent=intent,
        intent_confidence=confidence,
        sources=sources,
        retrieval_confidence=top_score,
        meets_retrieval_threshold=meets_threshold,
    )
    requires_human_support = immediate_human or should_escalate

    # 8. Grounded LLM Response Generation
    llm_service = get_llm_service()
    gen_result = await llm_service.generate_answer(
        question=req.message,
        intent=intent,
        category=category,
        confidence=confidence,
        sources=sources,
        meets_threshold=meets_threshold,
        conversation_history=history_docs,
        student_context=student_context,
    )

    final_response = gen_result.get("response", "")
    gen_requires_human = gen_result.get("requires_human_support", False)
    total_requires_human = bool(requires_human_support or gen_requires_human)

    # 9. Format source references for response & storage
    storage_sources: List[Dict[str, Any]] = []
    response_sources: List[SourceInfo] = []

    for s in sources:
        doc_id = s.get("document_id") or s.get("id")
        src_item = {
            "id": s.get("id"),
            "document_id": doc_id,
            "title": s.get("title"),
            "section": s.get("section"),
            "page": s.get("page"),
            "category": s.get("category"),
        }
        storage_sources.append(src_item)
        response_sources.append(SourceInfo(**src_item))

    # 10. Persist Assistant Message
    assistant_msg = new_message_doc(
        conversation_id=conv_id,
        sender=MESSAGE_SENDER_ASSISTANT,
        content=final_response,
        intent=intent,
        confidence=confidence,
        sources=storage_sources,
        requires_human_support=total_requires_human,
    )
    assistant_result = await db[MESSAGES].insert_one(assistant_msg)

    # 11. Update conversation metadata
    conv_update: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    if is_first_message:
        title = req.message[:50].strip() or "New Conversation"
        conv_update["title"] = title
    await db[CONVERSATIONS].update_one({"_id": conv_id}, {"$set": conv_update})

    return ChatResponseData(
        conversation_id=str(conv_id),
        message_id=str(assistant_result.inserted_id),
        response=final_response,
        message=final_response,
        intent=intent,
        confidence=confidence,
        sources=response_sources,
        requires_human_support=total_requires_human,
        requires_human=total_requires_human,
    )

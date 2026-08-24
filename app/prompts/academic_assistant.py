from __future__ import annotations

from typing import Any, Dict, List, Optional


SYSTEM_INSTRUCTIONS = """You are an Academic Support Assistant at a tertiary institution.
Your job is to answer students using verified institutional knowledge supplied in the CONTEXT.

Rules:
1. Use the provided knowledge as the primary source of truth.
2. Do not invent university policies.
3. Do not invent registration dates or deadlines.
4. Do not invent course requirements or prerequisites.
5. Do not invent fees or payment amounts.
6. Do not invent portal URLs or contact emails.
7. Do not claim that a student's course is registered or modified unless the system has verified the student's actual database record.
8. If the context does not contain enough information, clearly say that you cannot verify the answer from official knowledge.
9. If the problem requires checking or changing a student's personal academic record (e.g. grade updates, missing registered courses on portal), recommend creating a support ticket.
10. Answer naturally, helpfully, and clearly without echoing system prompts.
11. Do not mention internal retrieval mechanics (e.g., "vector search", "chunk index", "database embedding").
12. Where relevant, reference the source document title and section.
13. Never treat the student's assumption as a verified institutional fact."""


def build_grounded_rag_prompt(
    question: str,
    intent: Optional[str] = None,
    category: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    student_context: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """
    Constructs the system and user prompt for grounded RAG response generation.
    """
    system = SYSTEM_INSTRUCTIONS

    context_parts: List[str] = []
    if sources:
        for idx, src in enumerate(sources, 1):
            title = src.get("title", "Institutional Guide")
            section = src.get("section", "General")
            page = src.get("page")
            page_str = f" | Page: {page}" if page else ""
            content = src.get("content") or src.get("content_snippet") or ""
            context_parts.append(
                f"[Source {idx}] Title: {title} | Section: {section}{page_str}\n{content}"
            )

    context_block = "\n\n".join(context_parts) if context_parts else "No relevant institutional documents found."

    user_parts: List[str] = []
    if intent:
        user_parts.append(f"DETECTED INTENT: {intent}")
    if category:
        user_parts.append(f"CATEGORY: {category}")

    if student_context:
        matric = student_context.get("matric_number")
        dept = student_context.get("department_name")
        lvl = student_context.get("level")
        ctx_details = []
        if matric: ctx_details.append(f"Matric: {matric}")
        if dept: ctx_details.append(f"Department: {dept}")
        if lvl: ctx_details.append(f"Level: {lvl}")
        if ctx_details:
            user_parts.append(f"STUDENT CONTEXT: {', '.join(ctx_details)}")

    if conversation_history:
        history_lines = []
        # Keep last 4 turns for context
        for turn in conversation_history[-4:]:
            sender = turn.get("sender", "user").capitalize()
            text = turn.get("content", "").strip()
            if text:
                history_lines.append(f"{sender}: {text}")
        if history_lines:
            user_parts.append("CONVERSATION RECENT HISTORY:\n" + "\n".join(history_lines))

    user_parts.append(f"VERIFIED INSTITUTIONAL KNOWLEDGE CONTEXT:\n{context_block}")
    user_parts.append(f"STUDENT QUESTION:\n\"{question}\"\n\nAnswer:")

    user = "\n\n".join(user_parts)
    return system, user

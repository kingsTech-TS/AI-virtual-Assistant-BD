from __future__ import annotations

from typing import Any, Dict, List, Tuple


def build_intent_prompt(question: str, intents: List[str], keyword_hints: Dict[str, List[str]]) -> tuple[str, str]:
    system = (
        "You are an intent classifier for an academic support chatbot. "
        "Classify the student's question into exactly one of the provided intents. "
        "Output ONLY valid JSON with keys: intent (string), confidence (float 0..1)."
    )
    hints_lines = []
    for intent, kws in keyword_hints.items():
        if kws:
            hints_lines.append(f"- {intent}: keywords include {', '.join(kws)}")
    hints = "\n".join(hints_lines)
    user = (
        f"Intents allowed: {intents}.\n"
        f"Keyword hints:\n{hints}\n\n"
        f"Question: {question}\n"
        "Respond with JSON only, e.g. {\"intent\":\"course_registration\",\"confidence\":0.9}"
    )
    return system, user


def build_answer_prompt(question: str, intent: str, context: str | None = None) -> tuple[str, str]:
    system = (
        "You are an academic support assistant at a tertiary institution. "
        "Follow these rules strictly:\n"
        "1. Give concise and understandable answers.\n"
        "2. Prefer verified institutional information.\n"
        "3. Never invent university policies, deadlines, fees, examination dates, or official procedures.\n"
        "4. Clearly state when official information is unavailable.\n"
        "5. Recommend human support for complex or sensitive issues.\n"
        "6. Never expose or claim access to another student's private data.\n"
        "7. Do not claim to have performed backend actions (record updates, password changes, ticket creation).\n"
        "8. Use retrieved context when provided and mark it as verified information.\n"
    )
    context_block = ""
    if context:
        context_block = f"\n\nVerified institutional context:\n{context}\n"
    user = f"Student's question (intent={intent}): {question}{context_block}\n\nAnswer:"
    return system, user


def build_rag_prompt(question: str, intent: str, sources: List[Dict[str, Any]]) -> tuple[str, str]:
    context_lines = []
    for idx, s in enumerate(sources, 1):
        title = s.get("title", "Untitled")
        content = s.get("content") or s.get("content_snippet") or ""
        category = s.get("category", "")
        context_lines.append(f"[Source {idx}] {title} (category={category}):\n{content}")
    context = "\n\n".join(context_lines) if context_lines else ""
    return build_answer_prompt(question, intent, context)


def build_escalation_prompt(reason: str = "complex or sensitive issue") -> str:
    return (
        f"\n\nThis appears to be a {reason} that may require human assistance. "
        "Would you like me to create a support ticket for this issue?"
    )

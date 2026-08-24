from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.ai.prompt_manager import build_escalation_prompt
from app.core.logging import get_logger

logger = get_logger("ai.guardrails")

_ACTION_VERBS_RE = re.compile(
    r"\b(i have|i've|i will|i'll|i can|i am|i'm going to|we have|we've)\s+(updated|changed|reset|modified|created|closed|resolved|fixed|sent|emailed|registered|processed)\b",
    re.IGNORECASE,
)

_MATRIC_RE = re.compile(r"\b[A-Za-z0-9/-]{6,20}\b")

OFFICIAL_INFO_MISSING = (
    "I cannot verify official institutional information on this topic from my current knowledge base. "
    "For accurate details, please contact your department or the relevant administrative office."
)


def apply_guardrails(
    question: str,
    raw_response: str,
    sources: Optional[List[Dict[str, Any]]],
    confidence: float,
    intent: str,
) -> Dict[str, Any]:
    sources = sources or []
    response = (raw_response or "").strip()
    escalate = False
    reason: Optional[str] = None

    if _ACTION_VERBS_RE.search(response):
        escalate = True
        reason = "response claims backend actions"
        replacement = (
            "I cannot perform account or backend actions directly. For assistance, "
            "please contact support or create a support ticket."
        )
        response = _ACTION_VERBS_RE.sub(replacement, response, count=1)
        if response == replacement:
            pass
        else:
            response = replacement + "\n\n" + build_escalation_prompt(reason)

    institutional_intents = {
        "course_registration", "admission", "exam_schedule", "academic_calendar",
        "results", "fees", "portal_problem", "password_change", "departmental_issue",
    }
    if intent in institutional_intents and not sources and (confidence or 0) < 0.6:
        escalate = True
        reason = reason or "no institutional sources"
        prefix = OFFICIAL_INFO_MISSING + "\n\n"
        if not response.startswith(OFFICIAL_INFO_MISSING):
            response = prefix + response

    q_words = {w.lower() for w in re.findall(r"\b[A-Za-z0-9/-]+\b", question or "")}

    def _looks_like_matric(tok: str) -> bool:
        # A matric/ID token always contains a digit; plain words such as
        # "registration" or "prerequisites" must never be masked.
        if not any(ch.isdigit() for ch in tok):
            return False
        # Letter+digit mix or a slashed number looks like a matric, e.g.
        # "CSC/2019/001" or "U17CS1001".
        if any(ch.isalpha() for ch in tok) or "/" in tok:
            return True
        # Pure digits: only long runs look like student IDs. Keep years
        # (2024) and shorter numbers (fees, counts) intact.
        return len(tok) >= 7

    def _mask_other_matrics(match: re.Match) -> str:
        tok = match.group(0)
        if tok.lower() in q_words:
            return tok
        if not _looks_like_matric(tok):
            return tok
        return "[REDACTED]"

    response = _MATRIC_RE.sub(_mask_other_matrics, response)

    if "as an academic support assistant" in response.lower():
        response = response.split("I'm an academic support assistant", 1)[0].strip() or response
        response = response.split("As an academic support assistant", 1)[0].strip() or response

    if escalate:
        if build_escalation_prompt().strip() not in response:
            response = response.rstrip() + "\n\n" + build_escalation_prompt(reason or "sensitive or unverified matter")

    return {
        "response": response,
        "requires_human_support": escalate,
        "escalate_reason": reason,
    }

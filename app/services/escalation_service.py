from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

logger = None

_SENSITIVE_RECORD_PATTERNS = [
    re.compile(r"\b(dispute|disputed|unauthorized|missing payment|charged twice|deducted twice)\b", re.IGNORECASE),
    re.compile(r"\b(change my grade|update my cgpa|incorrect mark|exam grade error)\b", re.IGNORECASE),
    re.compile(r"\b(fraud|cheating|allegation|disciplinary|suspended|expelled)\b", re.IGNORECASE),
    re.compile(r"\b(talk to (a )?human|speak to (a )?staff|human agent|contact support|escalate)\b", re.IGNORECASE),
]


class EscalationService:
    def should_escalate(
        self,
        question: str,
        intent: str,
        intent_confidence: float,
        sources: List[Dict[str, Any]],
        retrieval_confidence: float,
        meets_retrieval_threshold: bool,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines whether the conversation requires escalation to human support personnel.
        """
        q = (question or "").lower()

        # 1. Direct sensitive / account modification pattern match
        for pat in _SENSITIVE_RECORD_PATTERNS:
            if pat.search(q):
                return True, "Request involves personal academic records, billing disputes, or explicit human support."

        # 2. Intent specifically indicates human support
        if intent == "human_support":
            return True, "Student explicitly requested human assistance."

        # 3. If confidence is very low and no sources were found
        if intent_confidence < 0.35 and not sources:
            return True, "Query understanding confidence is low and no matching knowledge was found."

        # 4. Institutional intent but retrieval score didn't meet minimum threshold
        institutional_intents = {
            "course_missing", "course_prerequisite", "course_not_available",
            "course_registration_error", "course_wrong_registration",
            "results", "fees", "portal_problem", "departmental_issue"
        }
        if intent in institutional_intents and not meets_retrieval_threshold and not sources:
            return True, "No verified institutional documents matched the query with sufficient confidence."

        return False, None


_escalation_service: Optional[EscalationService] = None


def get_escalation_service() -> EscalationService:
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = EscalationService()
    return _escalation_service

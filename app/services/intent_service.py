from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.ai.llm_client import BaseLLMClient, LLMUnavailableError, get_llm_client
from app.constants.intents import (
    INTENT_DESCRIPTIONS,
    INTENT_KEYWORDS,
    INTENT_TO_CATEGORY,
    INTENTS,
    Intent,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.intent import IntentClassificationResult

logger = get_logger("services.intent_service")

# Specific patterns indicating the user requires actual modification/check of personal account record
_HUMAN_RECORD_PATTERNS = [
    re.compile(r"\b(disappeared from my (portal|registration|account))\b", re.IGNORECASE),
    re.compile(r"\b(my grade is wrong|change my grade|wrong score on my transcript)\b", re.IGNORECASE),
    re.compile(r"\b(disputed registration|deducted fee twice|double payment)\b", re.IGNORECASE),
    re.compile(r"\b(talk to (a )?human|speak to (a )?person|need (a )?staff|human agent|create ticket)\b", re.IGNORECASE),
]

_COURSE_CODE_RE = re.compile(r"\b([a-zA-Z]{2,4}\s*\d{3})\b", re.IGNORECASE)


class IntentService:
    def __init__(self, llm: Optional[BaseLLMClient] = None):
        self._llm = llm

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def _rule_based_classify(self, question: str) -> IntentClassificationResult:
        q = (question or "").lower()
        # Clean common contractions for robust matching
        norm_q = q.replace("can't", "cannot").replace("isn't", "is not").replace("don't", "do not").replace("haven't", "have not")
        words = set(re.findall(r"[a-z0-9_/-]+", norm_q))
        if not words:
            return IntentClassificationResult(
                intent=Intent.UNKNOWN.value,
                category="general",
                confidence=0.1,
                requires_knowledge_search=False,
                requires_human=False,
            )

        # Check human trigger patterns
        requires_human = any(pat.search(norm_q) for pat in _HUMAN_RECORD_PATTERNS)

        best_intent = Intent.UNKNOWN.value
        best_score = 0.0

        for intent_enum, kws in INTENT_KEYWORDS.items():
            score = 0.0
            for kw in kws:
                kw_lower = kw.lower()
                if kw_lower in norm_q or kw_lower in q:
                    # Multi-word phrase matches get higher weight
                    match_weight = 2.5 if " " in kw_lower else 1.0
                    score += match_weight
            if score > best_score:
                best_score = score
                best_intent = intent_enum.value

        has_course_ref = bool(_COURSE_CODE_RE.search(norm_q) or "course" in norm_q or "subject" in norm_q or "module" in norm_q or "class" in norm_q)

        # Specialized semantic overrides for common student formulations
        if re.search(r"\b(missing|disappeared|do\s+not\s+have)\b", norm_q) and (has_course_ref or "list" in norm_q or "page" in norm_q or "portal" in norm_q):
            best_intent = Intent.COURSE_MISSING.value
            best_score = max(best_score, 4.0)
        elif re.search(r"\b(cannot\s+(?:i\s+)?(?:see|find|get|view)|not\s+(?:.*\s+)?(?:showing|listed|available|visible))\b", norm_q) and (has_course_ref or "list" in norm_q or "page" in norm_q or "portal" in norm_q):
            best_intent = Intent.COURSE_MISSING.value
            best_score = max(best_score, 4.0)
        elif re.search(r"\b(why\s+(?:cannot|can\s+not)\s+i\s+register)\b", norm_q) and (has_course_ref or "for" in norm_q):
            best_intent = Intent.COURSE_MISSING.value
            best_score = max(best_score, 4.0)
        elif re.search(r"\b(prerequisite|pre-requisite|prereq)\b", norm_q):
            best_intent = Intent.COURSE_PREREQUISITE.value
            best_score = max(best_score, 4.0)
        elif re.search(r"\b(not\s+available|unavailable|course\s+closed)\b", norm_q) and has_course_ref:
            best_intent = Intent.COURSE_NOT_AVAILABLE.value
            best_score = max(best_score, 3.5)

        if best_score <= 0.0:
            category = "general"
            confidence = 0.2
        else:
            category = INTENT_TO_CATEGORY.get(Intent(best_intent), "general") if best_intent in INTENTS else "general"
            confidence = min(0.96, max(0.45, (best_score / max(2, len(words) * 0.4)) + 0.5))

        if best_intent == Intent.HUMAN_SUPPORT.value:
            requires_human = True

        requires_search = best_intent not in (Intent.HUMAN_SUPPORT.value, Intent.UNKNOWN.value)

        return IntentClassificationResult(
            intent=best_intent,
            category=category,
            confidence=round(confidence, 3),
            requires_knowledge_search=requires_search,
            requires_human=requires_human,
        )

    def _build_llm_prompt(self, question: str) -> tuple[str, str]:
        system = (
            "You are a semantic intent classifier for a university academic support chatbot.\n"
            "Analyze the student's question and determine the underlying academic intent.\n"
            "Available intents:\n"
            + "\n".join(f"- {i}: {INTENT_DESCRIPTIONS.get(Intent(i), '')}" for i in INTENTS)
            + "\n\nOutput STRICT JSON with schema:\n"
            "{\n"
            '  "intent": "<intent_string>",\n'
            '  "category": "<category_string>",\n'
            '  "confidence": <float 0.0 to 1.0>,\n'
            '  "requires_knowledge_search": <boolean>,\n'
            '  "requires_human": <boolean>\n'
            "}"
        )
        user = f"Student Question: {question}\nJSON Response:"
        return system, user

    async def classify(self, question: str) -> IntentClassificationResult:
        if not question or not question.strip():
            return IntentClassificationResult(
                intent=Intent.UNKNOWN.value,
                category="general",
                confidence=0.1,
                requires_knowledge_search=False,
                requires_human=False,
            )

        # If LLM classification is disabled in config, use deterministic classifier
        if not settings.USE_LLM_INTENT:
            return self._rule_based_classify(question)

        try:
            system, user = self._build_llm_prompt(question)
            prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
            structured_data = await self.llm.generate_structured(prompt)
            
            # Validate with Pydantic schema
            parsed = IntentClassificationResult(**structured_data)
            # Ensure category matches standard mapping if not provided correctly
            if parsed.intent in INTENTS:
                expected_category = INTENT_TO_CATEGORY.get(Intent(parsed.intent), parsed.category)
                parsed.category = expected_category
            return parsed
        except (LLMUnavailableError, Exception) as e:
            logger.info(f"LLM intent classification failed or unavailable ({e}); falling back to deterministic classifier.")
            return self._rule_based_classify(question)


_intent_service: Optional[IntentService] = None


def get_intent_service() -> IntentService:
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentService()
    return _intent_service

from __future__ import annotations

import json
import re
from typing import Any, Dict

from app.ai.llm_client import BaseLLMClient, LLMUnavailableError, get_llm_client
from app.ai.prompt_manager import build_intent_prompt
from app.constants.intents import INTENT_KEYWORDS, INTENTS, Intent
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.intent_classifier")


class IntentClassifier:
    def __init__(self, llm: BaseLLMClient | None = None):
        self._llm = llm

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def _keyword_fallback(self, question: str) -> Dict[str, Any]:
        q = question.lower()
        words = set(re.findall(r"[a-z0-9_/-]+", q))
        if not words:
            return {"intent": Intent.UNKNOWN.value, "confidence": 0.1}
        best_intent = Intent.UNKNOWN.value
        best_score = 0.0
        for intent, kws in INTENT_KEYWORDS.items():
            score = 0.0
            matched = 0
            for kw in kws:
                if kw.lower() in q:
                    matched += 1
                    score += 1.0 + (0.5 if " " in kw else 0.0)
            if score > best_score:
                best_score = score
                best_intent = intent
        if best_score <= 0:
            return {"intent": Intent.UNKNOWN.value, "confidence": 0.1}
        confidence = min(1.0, best_score / max(3, len(words)) + 0.3)
        return {"intent": best_intent, "confidence": round(confidence, 3)}

    async def classify(self, question: str) -> Dict[str, Any]:
        # Skip the LLM round-trip unless explicitly enabled — the keyword
        # classifier is a solid default and keeps us under rate limits.
        if not settings.USE_LLM_INTENT:
            return self._keyword_fallback(question)
        try:
            system, user = build_intent_prompt(question, list(INTENTS), INTENT_KEYWORDS)
            prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
            result = await self.llm.generate_structured(prompt)
            intent = (result.get("intent") or "").strip().lower()
            confidence = result.get("confidence")
            if intent not in INTENTS:
                raise ValueError(f"Unknown intent {intent}")
            try:
                cf = float(confidence)
                cf = max(0.0, min(1.0, cf))
            except (TypeError, ValueError):
                cf = 0.5
            return {"intent": intent, "confidence": cf}
        except LLMUnavailableError:
            logger.info("LLM unavailable for intent classification; using keyword fallback")
        except Exception as e:
            logger.warning(f"Intent classification via LLM failed: {e}; using keyword fallback")
        return self._keyword_fallback(question)


_intent_classifier: IntentClassifier | None = None


def get_intent_classifier() -> IntentClassifier:
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier

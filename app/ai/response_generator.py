from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.ai.llm_client import BaseLLMClient, LLMUnavailableError, get_llm_client
from app.ai.prompt_manager import build_escalation_prompt, build_rag_prompt
from app.core.logging import get_logger

logger = get_logger("ai.response_generator")

FALLBACK_MESSAGE = (
    "I'm currently unable to process your request. "
    "You can try again shortly or create a support ticket for assistance."
)

ESCALATION_OFFER = build_escalation_prompt("complex or sensitive issue")


class ResponseGenerator:
    INSTITUTIONAL_INTENTS = {
        "course_registration",
        "admission",
        "exam_schedule",
        "academic_calendar",
        "results",
        "fees",
        "portal_problem",
        "password_change",
        "departmental_issue",
    }

    def __init__(self, llm: Optional[BaseLLMClient] = None):
        self._llm = llm

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def generate(
        self,
        question: str,
        intent: str,
        confidence: float,
        sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        sources = sources or []
        cf = float(confidence) if isinstance(confidence, (int, float)) else 0.0
        needs_escalation = False

        if cf < 0.3:
            needs_escalation = True
            return {
                "response": (
                    "I'm not confident I understood your question correctly. "
                    + ESCALATION_OFFER
                ),
                "requires_human_support": True,
            }

        institutional = intent in self.INSTITUTIONAL_INTENTS
        if institutional and not sources and cf < 0.6:
            needs_escalation = True

        try:
            system, user = build_rag_prompt(question, intent, sources)
            prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
            response_text = await self.llm.generate(prompt, temperature=0.2, max_tokens=1500)
        except LLMUnavailableError as e:
            logger.warning(f"LLM unavailable: {e}")
            return {
                "response": FALLBACK_MESSAGE,
                "requires_human_support": True,
            }
        except Exception as e:
            logger.exception("Unexpected error in response_generator.generate")
            return {
                "response": FALLBACK_MESSAGE,
                "requires_human_support": True,
            }

        if needs_escalation:
            response_text = response_text.rstrip() + ESCALATION_OFFER

        return {
            "response": response_text,
            "requires_human_support": needs_escalation,
        }


_generator: Optional[ResponseGenerator] = None


def get_response_generator() -> ResponseGenerator:
    global _generator
    if _generator is None:
        _generator = ResponseGenerator()
    return _generator

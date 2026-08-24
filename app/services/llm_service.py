from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.ai.guardrails import apply_guardrails
from app.ai.llm_client import BaseLLMClient, LLMUnavailableError, get_llm_client
from app.core.logging import get_logger
from app.prompts.academic_assistant import build_grounded_rag_prompt

logger = get_logger("services.llm_service")

FALLBACK_MESSAGE = (
    "I'm currently unable to generate a verified response. "
    "Please try again shortly or submit a support ticket to connect with departmental staff."
)

UNVERIFIED_INFO_MESSAGE = (
    "I couldn't find enough verified information in the official academic knowledge base to answer that accurately. "
    "Please consult the relevant departmental office or submit a support ticket for assistance."
)


class LLMService:
    def __init__(self, llm: Optional[BaseLLMClient] = None):
        self._llm = llm

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def generate_answer(
        self,
        question: str,
        intent: str,
        category: str,
        confidence: float,
        sources: List[Dict[str, Any]],
        meets_threshold: bool,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        student_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates a grounded academic response using the LLM and retrieved knowledge.
        Applies anti-hallucination guardrails and source verification.
        """
        # If institutional query and zero sources found or relevance below threshold
        institutional_intents = {
            "course_missing", "course_prerequisite", "course_not_available",
            "course_registration_error", "course_registration_deadline",
            "course_add_drop", "course_wrong_registration",
            "results", "fees", "portal_problem", "departmental_issue", "examination",
        }

        if not sources and intent in institutional_intents:
            return {
                "response": UNVERIFIED_INFO_MESSAGE,
                "requires_human_support": True,
            }

        system, user = build_grounded_rag_prompt(
            question=question,
            intent=intent,
            category=category,
            sources=sources,
            conversation_history=conversation_history,
            student_context=student_context,
        )

        try:
            prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
            raw_response = await self.llm.generate(prompt, temperature=0.2, max_tokens=1500)
        except LLMUnavailableError as e:
            logger.warning(f"LLM unavailable for response generation: {e}")
            return {
                "response": FALLBACK_MESSAGE,
                "requires_human_support": True,
            }
        except Exception as e:
            logger.exception(f"Unexpected error in LLM generation: {e}")
            return {
                "response": FALLBACK_MESSAGE,
                "requires_human_support": True,
            }

        # Apply guardrails (mask accidental sensitive tokens, prevent unauthorized backend claims)
        guardrail_result = apply_guardrails(
            question=question,
            raw_response=raw_response,
            sources=sources,
            confidence=confidence,
            intent=intent,
        )
        final_response = guardrail_result.get("response", raw_response)
        requires_human = guardrail_result.get("requires_human_support", False)

        return {
            "response": final_response,
            "requires_human_support": requires_human,
        }


_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

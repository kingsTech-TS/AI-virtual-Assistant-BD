from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("services.reranking_service")

# Regex to detect important academic entities (e.g., CSC 301, MAT 101, 2026/2027, 300L, 300 Level)
_ENTITY_PATTERNS = [
    re.compile(r"\b([a-zA-Z]{2,4}\s*\d{3})\b", re.IGNORECASE),  # Course codes like CSC 301
    re.compile(r"\b(\d{4}/\d{4})\b"),                          # Academic sessions like 2026/2027
    re.compile(r"\b(\d{3}\s*(?:level|l))\b", re.IGNORECASE),   # Levels like 300 Level, 300L
]


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    na = math.sqrt(sum(x * x for x in vec_a)) or 1.0
    nb = math.sqrt(sum(y * y for y in vec_b)) or 1.0
    return max(0.0, min(1.0, dot / (na * nb)))


def _extract_exact_entities(text: str) -> List[str]:
    entities: List[str] = []
    for pat in _ENTITY_PATTERNS:
        matches = pat.findall(text or "")
        for m in matches:
            norm = re.sub(r"\s+", " ", m).strip().upper()
            entities.append(norm)
    return entities


class RerankingService:
    def __init__(self, min_relevance_score: Optional[float] = None):
        self.min_relevance_score = min_relevance_score or getattr(settings, "RAG_MIN_RELEVANCE_SCORE", 0.60)

    def rerank_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        query_vector: Optional[List[float]] = None,
        intent: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 4,
    ) -> Tuple[List[Dict[str, Any]], float, bool]:
        """
        Reranks a candidate list of knowledge chunks using hybrid scoring:
        - Vector similarity
        - Keyword & lexical relevance
        - Exact entity matching
        - Intent & section alignment
        
        Returns: (ranked_chunks, top_score, meets_confidence_threshold)
        """
        if not chunks:
            return [], 0.0, False

        q_lower = query.lower()
        q_words = set(re.findall(r"[a-z0-9_/-]+", q_lower))
        exact_entities = _extract_exact_entities(query)

        scored_candidates: List[Tuple[float, Dict[str, Any]]] = []

        for chunk in chunks:
            title = (chunk.get("title") or "").lower()
            section = (chunk.get("section") or "").lower()
            content = (chunk.get("content") or "").lower()
            chunk_category = (chunk.get("category") or "").lower()
            chunk_intents = [str(i).lower() for i in (chunk.get("intent") or [])]
            chunk_emb = chunk.get("embedding") or []

            # 1. Vector similarity
            vec_sim = 0.0
            has_vector = False
            if query_vector and chunk_emb and len(query_vector) == len(chunk_emb):
                vec_sim = _cosine_similarity(query_vector, chunk_emb)
                has_vector = True
            elif "score" in chunk and isinstance(chunk["score"], (int, float)):
                vec_sim = min(1.0, float(chunk["score"]))
                has_vector = True

            # 2. Keyword & Section Overlap
            combined_text = f"{title} {section} {content}"
            chunk_words = set(re.findall(r"[a-z0-9_/-]+", combined_text))
            overlap_count = len(q_words & chunk_words)
            lexical_sim = overlap_count / max(1, len(q_words))

            # 3. Exact Entity Boost
            entity_boost = 0.0
            if exact_entities:
                matched_entities = sum(1 for e in exact_entities if e.lower() in combined_text)
                entity_boost = matched_entities / len(exact_entities)

            # 4. Intent & Section alignment
            intent_align = 0.0
            if intent:
                intent_clean = intent.replace("_", " ").lower()
                if intent.lower() in chunk_intents:
                    intent_align = 1.0
                elif intent_clean in section or section in intent_clean:
                    intent_align = 0.90
                elif "missing" in q_lower and "missing" in section:
                    intent_align = 1.0
                elif "prerequisite" in q_lower and "prerequisite" in section:
                    intent_align = 1.0
                elif "fee" in intent_clean and "fee" in section:
                    intent_align = 1.0
                elif "exam" in intent_clean and "exam" in section:
                    intent_align = 1.0

            if category and chunk_category == category.lower():
                intent_align = max(intent_align, 0.5)

            # Calculate composite hybrid score based on available features
            if has_vector:
                if exact_entities:
                    composite_score = (0.35 * vec_sim) + (0.25 * lexical_sim) + (0.20 * entity_boost) + (0.20 * intent_align)
                else:
                    composite_score = (0.45 * vec_sim) + (0.30 * lexical_sim) + (0.25 * intent_align)
            else:
                if exact_entities:
                    composite_score = (0.45 * lexical_sim) + (0.30 * entity_boost) + (0.25 * intent_align)
                else:
                    composite_score = (0.55 * lexical_sim) + (0.45 * intent_align)

            # Boost if section title or content strongly aligns with topic
            if intent_align >= 0.8:
                composite_score = min(1.0, composite_score + 0.15)
            if exact_entities and entity_boost >= 0.9:
                composite_score = min(1.0, composite_score + 0.15)

            composite_score = round(composite_score, 4)
            
            chunk_copy = dict(chunk)
            chunk_copy["rerank_score"] = composite_score
            chunk_copy["score"] = composite_score
            scored_candidates.append((composite_score, chunk_copy))

        # Sort descending by composite score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        top_score = scored_candidates[0][0] if scored_candidates else 0.0
        final_chunks = [c for _, c in scored_candidates[:top_k]]
        
        # Check if top score meets the threshold
        meets_threshold = top_score >= self.min_relevance_score

        return final_chunks, top_score, meets_threshold


_reranking_service: Optional[RerankingService] = None


def get_reranking_service() -> RerankingService:
    global _reranking_service
    if _reranking_service is None:
        _reranking_service = RerankingService()
    return _reranking_service

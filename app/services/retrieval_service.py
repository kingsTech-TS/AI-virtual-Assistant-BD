from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from bson import ObjectId

from app.core.config import settings
from app.core.logging import get_logger
from app.database.collections import KNOWLEDGE_BASE
from app.services.embedding_service import get_embedding_service
from app.services.reranking_service import get_reranking_service
from app.services.vector_search_service import get_vector_search_service
from app.utils.ids import to_obj_id

logger = get_logger("services.retrieval_service")

# Query normalization mappings
_NORMALIZATION_MAP = {
    r"\bcant\b": "can not",
    r"\bcan't\b": "can not",
    r"\bisnt\b": "is not",
    r"\bisn't\b": "is not",
    r"\bdont\b": "do not",
    r"\bdon't\b": "do not",
    r"\bwhere is\b": "location of",
    r"\bprereq\b": "prerequisite",
    r"\bprereqs\b": "prerequisites",
}


def normalize_search_query(query: str) -> str:
    """
    Normalizes student query into a high-signal search representation
    without introducing unprovided facts.
    """
    q = (query or "").strip().lower()
    for pat, rep in _NORMALIZATION_MAP.items():
        q = re.sub(pat, rep, q, flags=re.IGNORECASE)
    # Course codes spacing: "CSC301" -> "CSC 301"
    q = re.sub(r"\b([a-zA-Z]{2,4})(\d{3})\b", r"\1 \2", q)
    return q


class RetrievalService:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.vector_search_service = get_vector_search_service()
        self.reranking_service = get_reranking_service()

    async def _fetch_mongo_candidate_chunks(
        self,
        db,
        category: Optional[str] = None,
        department_id: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Fetches candidate published knowledge base chunks from MongoDB.
        Searches matching category and general published documents.
        """
        query: Dict[str, Any] = {"status": "published"}
        if department_id:
            dept_oid = to_obj_id(department_id)
            query["$or"] = [{"department_id": None}, {"department_id": dept_oid}]

        # If a category is requested, we query matching category or general
        if category and category != "general":
            query["$or"] = [
                {"category": category},
                {"category": "general"},
                {"category": None},
            ]

        cursor = db[KNOWLEDGE_BASE].find(
            query,
            {
                "_id": 1,
                "document_id": 1,
                "title": 1,
                "section": 1,
                "category": 1,
                "intent": 1,
                "content": 1,
                "page": 1,
                "chunk_index": 1,
                "department_id": 1,
                "source": 1,
                "embedding": 1,
                "version": 1,
            }
        ).limit(limit)

        return await cursor.to_list(length=limit)

    async def retrieve(
        self,
        db,
        question: str,
        intent: Optional[str] = None,
        category: Optional[str] = None,
        department_id: Optional[str] = None,
        top_k: int = 4,
    ) -> Tuple[List[Dict[str, Any]], float, bool]:
        """
        Main retrieval method performing:
        1. Query normalization
        2. Query embedding generation
        3. Atlas Vector Search
        4. Fallback MongoDB candidate retrieval
        5. Hybrid reranking and relevance threshold validation
        
        Returns: (final_chunks, confidence_score, meets_relevance_threshold)
        """
        clean_query = normalize_search_query(question)
        
        # Generate query vector if enabled or available
        query_vector: List[float] = []
        try:
            query_vector = await self.embedding_service.generate_embedding(clean_query)
        except Exception as e:
            logger.info(f"Query embedding generation failed: {e}")
            query_vector = []

        candidates: List[Dict[str, Any]] = []

        # 1. Attempt Atlas Vector Search
        if query_vector:
            vs_results = await self.vector_search_service.search(
                db=db,
                query_vector=query_vector,
                top_k=getattr(settings, "RAG_TOP_CANDIDATES", 8),
                category=category,
                department_id=department_id,
            )
            if vs_results:
                candidates.extend(vs_results)

        # 2. If vector search yielded few/no candidates, pull published candidate pool from MongoDB
        if len(candidates) < 3:
            mongo_candidates = await self._fetch_mongo_candidate_chunks(
                db=db,
                category=category,
                department_id=department_id,
                limit=30,
            )
            # Merge and deduplicate candidates by _id
            seen_ids = {str(c.get("_id")) for c in candidates}
            for mc in mongo_candidates:
                cid = str(mc.get("_id"))
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    candidates.append(mc)

        if not candidates:
            return [], 0.0, False

        # 3. Rerank candidates using hybrid scoring
        ranked_chunks, top_score, meets_threshold = self.reranking_service.rerank_chunks(
            query=clean_query,
            chunks=candidates,
            query_vector=query_vector,
            intent=intent,
            category=category,
            top_k=top_k,
        )

        # Map to structured dictionary items
        formatted_sources: List[Dict[str, Any]] = []
        for c in ranked_chunks:
            oid = c.get("_id")
            id_str = str(oid) if isinstance(oid, ObjectId) else str(oid or "")
            content = c.get("content") or ""
            snippet = content[:400] + ("..." if len(content) > 400 else "")
            
            formatted_sources.append({
                "id": id_str,
                "document_id": c.get("document_id") or id_str,
                "title": c.get("title") or "Academic Policy",
                "section": c.get("section") or "General",
                "category": c.get("category") or "general",
                "content": content,
                "content_snippet": snippet,
                "page": c.get("page"),
                "chunk_index": c.get("chunk_index", 0),
                "source": c.get("source"),
                "department_id": str(c.get("department_id")) if c.get("department_id") else None,
                "score": c.get("score", 0.0),
                "rerank_score": c.get("rerank_score", 0.0),
            })

        return formatted_sources, top_score, meets_threshold


_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service

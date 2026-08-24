from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.ai.embeddings import BaseEmbeddingProvider, get_embeddings_provider
from app.core.config import settings
from app.core.logging import get_logger
from app.database.collections import KNOWLEDGE_BASE
from app.utils.ids import to_obj_id

logger = get_logger("ai.rag_service")


def _cosine_sim(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


class RAGService:
    def __init__(self, embeddings: Optional[BaseEmbeddingProvider] = None):
        self._embeddings = embeddings

    @property
    def embeddings(self) -> BaseEmbeddingProvider:
        if self._embeddings is None:
            self._embeddings = get_embeddings_provider()
        return self._embeddings

    async def _try_vector_search(
        self,
        db,
        query_vector: List[float],
        top_k: int,
        category_filter: Optional[str],
        department_id,
    ) -> Optional[List[Dict[str, Any]]]:
        if not query_vector:
            return None
        try:
            vector_index_name = getattr(settings, "VECTOR_SEARCH_INDEX", "vector_index")
            vector_stage: Dict[str, Any] = {
                "index": vector_index_name,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": max(top_k * 10, 50),
                "limit": top_k,
            }
            match_filter: Dict[str, Any] = {"status": "published"}
            if category_filter:
                match_filter["category"] = category_filter
            if department_id:
                match_filter["$or"] = [
                    {"department_id": None},
                    {"department_id": to_obj_id(department_id)},
                ]
            vector_stage["filter"] = match_filter

            pipeline = [
                {"$vectorSearch": vector_stage},
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            ]
            cursor = db[KNOWLEDGE_BASE].aggregate(pipeline)
            return await cursor.to_list(length=top_k)
        except Exception as e:
            logger.info(f"Atlas Vector Search index unavailable, using semantic + keyword fallback: {e}")
            return None

    async def _fallback_search(
        self,
        db,
        question: str,
        category_filter: Optional[str],
        department_id,
        top_k: int,
        query_vector: List[float],
    ) -> List[Dict[str, Any]]:
        q = {"status": "published"}
        if category_filter:
            q["category"] = category_filter
        if department_id:
            q["$or"] = [{"department_id": None}, {"department_id": to_obj_id(department_id)}]
        q_words = set(re.findall(r"[a-z0-9_/-]+", question.lower()))
        cursor = db[KNOWLEDGE_BASE].find(q, {"embedding": 1, "title": 1, "content": 1, "category": 1, "source": 1, "department_id": 1})
        items = await cursor.to_list(length=top_k * 5)
        scored = []
        for it in items:
            title = (it.get("title") or "").lower()
            content = (it.get("content") or "").lower()
            overlap = len(q_words & set(re.findall(r"[a-z0-9_/-]+", title + " " + content)))
            score = overlap / max(1, len(q_words))
            emb = it.get("embedding") or []
            if emb and query_vector and len(emb) == len(query_vector):
                score = 0.6 * _cosine_sim(emb, query_vector) + 0.4 * score
            scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for s, it in scored[:top_k]:
            it2 = dict(it)
            it2["score"] = s
            results.append(it2)
        return results

    async def retrieve(
        self,
        db,
        question: str,
        category_filter: Optional[str] = None,
        department_id=None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        top_k = max(1, min(top_k, 10))
        query_vector: List[float] = []
        if settings.USE_QUERY_EMBEDDINGS:
            try:
                query_vector = await self.embeddings.embed_one(question)
            except Exception:
                query_vector = []

        vs_results = await self._try_vector_search(db, query_vector, top_k, category_filter, department_id)
        if vs_results is None or len(vs_results) == 0:
            vs_results = await self._fallback_search(db, question, category_filter, department_id, top_k, query_vector)

        mapped: List[Dict[str, Any]] = []
        for doc in vs_results:
            d = dict(doc)
            oid = d.get("_id")
            id_str = str(oid) if isinstance(oid, ObjectId) else str(oid or "")
            content = d.get("content") or ""
            snippet = content[:400] + ("..." if len(content) > 400 else "")
            dept_id = d.get("department_id")
            mapped.append({
                "id": id_str,
                "title": d.get("title"),
                "category": d.get("category"),
                "content": content,
                "content_snippet": snippet,
                "source": d.get("source"),
                "department_id": str(dept_id) if dept_id else None,
                "score": d.get("score"),
            })
        return mapped


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.database.collections import KNOWLEDGE_BASE
from app.utils.ids import to_obj_id

logger = get_logger("services.vector_search_service")


class VectorSearchService:
    async def search(
        self,
        db,
        query_vector: List[float],
        top_k: int = 8,
        category: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Executes a MongoDB Atlas $vectorSearch aggregation on published knowledge chunks.
        Returns candidate document chunks with vector similarity scores, or None if vector search is unavailable.
        """
        if not query_vector:
            return None

        try:
            vector_index_name = getattr(settings, "VECTOR_SEARCH_INDEX", "vector_index")
            num_candidates = max(top_k * 10, 50)
            
            vector_stage: Dict[str, Any] = {
                "index": vector_index_name,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": num_candidates,
                "limit": top_k,
            }

            match_filter: Dict[str, Any] = {"status": "published"}
            if category and category != "general":
                match_filter["category"] = category
            if department_id:
                dept_oid = to_obj_id(department_id)
                match_filter["$or"] = [
                    {"department_id": None},
                    {"department_id": dept_oid},
                ]
            vector_stage["filter"] = match_filter

            pipeline = [
                {"$vectorSearch": vector_stage},
                {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
            ]

            cursor = db[KNOWLEDGE_BASE].aggregate(pipeline)
            results = await cursor.to_list(length=top_k)
            return results
        except Exception as e:
            logger.info(f"Atlas Vector Search aggregate unavailable ({e}); falling back to hybrid retrieval.")
            return None


_vector_search_service: Optional[VectorSearchService] = None


def get_vector_search_service() -> VectorSearchService:
    global _vector_search_service
    if _vector_search_service is None:
        _vector_search_service = VectorSearchService()
    return _vector_search_service

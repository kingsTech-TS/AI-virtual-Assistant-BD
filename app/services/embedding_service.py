from __future__ import annotations

from typing import List, Optional
from app.ai.embeddings import BaseEmbeddingProvider, get_embeddings_provider
from app.core.logging import get_logger

logger = get_logger("services.embedding_service")


class EmbeddingService:
    def __init__(self, provider: Optional[BaseEmbeddingProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> BaseEmbeddingProvider:
        if self._provider is None:
            self._provider = get_embeddings_provider()
        return self._provider

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a single normalized vector embedding for the input text."""
        if not text or not text.strip():
            return []
        try:
            return await self.provider.embed_one(text)
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}. Returning empty vector fallback.")
            return []

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of texts."""
        if not texts:
            return []
        try:
            return await self.provider.embed(texts)
        except Exception as e:
            logger.warning(f"Batch embedding generation failed: {e}. Returning fallback vectors.")
            return [[] for _ in texts]


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


async def generate_embedding(text: str) -> List[float]:
    """Convenience functional wrapper for single text embedding."""
    service = get_embedding_service()
    return await service.generate_embedding(text)

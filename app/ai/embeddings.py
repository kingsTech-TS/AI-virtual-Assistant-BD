from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import httpx

from app.ai.llm_client import LLMUnavailableError, parse_retry_after, rate_limit_circuit
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.embeddings")


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        ...

    async def embed_one(self, text: str) -> List[float]:
        res = await self.embed([text])
        return res[0]


class PseudoEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic pseudo embeddings for DEV ONLY when no API key is set.
    NOT suitable for real vector search quality, but allows the pipeline to function."""

    DIM = 384

    def __init__(self, dim: int = DIM):
        self.dim = dim

    async def embed(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = []
        for t in texts:
            vec = [0.0] * self.dim
            ts = t or ""
            for i, ch in enumerate(ts):
                vec[(i * 7 + ord(ch)) % self.dim] += (ord(ch) % 13) / 13.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            results.append([v / norm for v in vec])
        return results


class OpenAICompatibleEmbeddings(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if rate_limit_circuit.is_open():
            raise LLMUnavailableError(
                f"rate-limit cooldown active "
                f"({rate_limit_circuit.seconds_remaining():.0f}s remaining); skipping embeddings call"
            )
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {"model": self.model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=body, headers=headers)
            # Share the cooldown with the chat client — same account, same quota.
            if resp.status_code == 429:
                rate_limit_circuit.trip(parse_retry_after(resp))
                raise LLMUnavailableError(
                    f"embeddings rate limited (429); pausing gateway calls for "
                    f"{rate_limit_circuit.seconds_remaining():.0f}s"
                )
            resp.raise_for_status()
            data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            return [it["embedding"] for it in items]
        except LLMUnavailableError:
            raise
        except Exception as e:
            raise LLMUnavailableError(f"Embeddings request failed: {e}") from e


_provider: Optional[BaseEmbeddingProvider] = None


def get_embeddings_provider() -> BaseEmbeddingProvider:
    global _provider
    if _provider is not None:
        return _provider
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
    model = settings.EMBEDDING_MODEL
    if api_key and model:
        _provider = OpenAICompatibleEmbeddings(api_key=api_key, model=model, base_url=settings.EMBEDDING_BASE_URL)
    else:
        logger.warning("No embeddings configured; using pseudo-embedding provider. Vector search quality will be poor.")
        _provider = PseudoEmbeddingProvider()
    return _provider

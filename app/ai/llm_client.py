from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.llm_client")


class LLMUnavailableError(Exception):
    pass


class _RateLimitCircuit:
    """Process-wide cooldown shared by every Vercel AI Gateway call.

    A 429 on any endpoint (chat or embeddings) opens the circuit for a short
    window. While it is open, all gateway calls fail fast to their local
    fallbacks (keyword intent, pseudo-embeddings, canned reply) instead of
    hammering an account that is already being throttled.
    """

    DEFAULT_COOLDOWN = 30.0

    def __init__(self) -> None:
        self._open_until = 0.0

    def seconds_remaining(self) -> float:
        return max(0.0, self._open_until - time.monotonic())

    def is_open(self) -> bool:
        return self.seconds_remaining() > 0.0

    def trip(self, cooldown: Optional[float] = None) -> None:
        cd = cooldown if cooldown and cooldown > 0 else self.DEFAULT_COOLDOWN
        self._open_until = max(self._open_until, time.monotonic() + cd)


rate_limit_circuit = _RateLimitCircuit()


def parse_retry_after(resp: httpx.Response) -> Optional[float]:
    """Parse a Retry-After header (seconds) into a bounded float, or None."""
    raw = resp.headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, min(float(raw), 120.0))
    except (TypeError, ValueError):
        return None


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        ...

    @abstractmethod
    async def generate_structured(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        ...


class _StubRaisingLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        raise LLMUnavailableError("LLM_API_KEY not configured")

    async def generate_structured(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        raise LLMUnavailableError("LLM_API_KEY not configured")


class OpenAICompatibleLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, timeout: float = 30.0, retries: int = 2):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout = timeout
        self.retries = retries

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if rate_limit_circuit.is_open():
            raise LLMUnavailableError(
                f"rate-limit cooldown active "
                f"({rate_limit_circuit.seconds_remaining():.0f}s remaining); skipping call to {url}"
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_exc: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=body, headers=headers)

                # Rate limited: do NOT retry — that only adds load to an
                # already-throttled account. Open a shared cooldown so every
                # other gateway call fails fast until it clears.
                if resp.status_code == 429:
                    rate_limit_circuit.trip(parse_retry_after(resp))
                    raise LLMUnavailableError(
                        f"rate limited (429) by {url}; pausing gateway calls for "
                        f"{rate_limit_circuit.seconds_remaining():.0f}s"
                    )

                # Transient upstream failure: retry with backoff.
                if resp.status_code >= 500:
                    last_exc = LLMUnavailableError(f"LLM upstream error {resp.status_code}")
                    if attempt < self.retries:
                        await asyncio.sleep(0.5 * (1.5**attempt))
                        continue
                    break

                # Client error (400/401/403/404...): not transient — fail fast.
                # Retrying just repeats the same rejection and adds load.
                if resp.status_code >= 400:
                    snippet = resp.text[:300].replace("\n", " ").strip()
                    raise LLMUnavailableError(
                        f"LLM request rejected ({resp.status_code}) at {url}: {snippet!r}"
                    )

                content_type = resp.headers.get("content-type", "")
                if "json" not in content_type.lower():
                    snippet = resp.text[:200].replace("\n", " ").strip()
                    raise LLMUnavailableError(
                        f"Expected JSON from {url} but got '{content_type}' "
                        f"(status {resp.status_code}). Check LLM_BASE_URL includes the API "
                        f"path prefix (e.g. it should end with '/v1'). Body starts: {snippet!r}"
                    )
                return resp.json()
            except LLMUnavailableError:
                # Deterministic errors we raised deliberately — do not retry.
                raise
            except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                # The gateway accepted the request but didn't respond in time.
                # Retrying re-runs an expensive generation and piles more load
                # onto an already-slow/throttled account — so fail fast to the
                # local fallback instead of waiting out another full timeout.
                raise LLMUnavailableError(
                    f"LLM timed out after {self.timeout:.0f}s at {url}; not retrying"
                ) from e
            except Exception as e:
                # Connection-level errors are transient: retry with backoff.
                last_exc = e
                if attempt < self.retries:
                    await asyncio.sleep(0.5 * (1.5**attempt))
                continue
        raise LLMUnavailableError(f"LLM request failed: {last_exc}") from last_exc

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1500),
        }
        data = await self._post("/chat/completions", body)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMUnavailableError(f"Unexpected LLM response structure: {data}") from e

    async def generate_structured(self, prompt: str, response_schema: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        import json
        system = "You are a precise JSON generator. Output ONLY valid JSON with no extra text."
        body_msg = prompt + "\n\nOutput ONLY valid JSON."
        text = await self.generate(body_msg, system_prompt=system, temperature=0.0, max_tokens=2000)
        try:
            first = text.find("{")
            last = text.rfind("}")
            if first >= 0 and last > first:
                text = text[first:last + 1]
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Failed to parse structured LLM output: {text[:200]}")
            raise LLMUnavailableError(f"Invalid structured response: {e}") from e


_llm_client: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    global _llm_client
    if _llm_client is not None:
        return _llm_client
    if settings.LLM_API_KEY:
        _llm_client = OpenAICompatibleLLMClient(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
        )
    else:
        _llm_client = _StubRaisingLLMClient()
    return _llm_client

from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.ai.llm_client import LLMUnavailableError, OpenAICompatibleLLMClient


@pytest.mark.asyncio
async def test_chat_new_conversation(client: AsyncClient, student_user):
    payload = {
        "conversation_id": None,
        "message": "How do I register for my semester courses?",
    }
    response = await client.post("/api/v1/chat", json=payload, headers=student_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    res_data = data["data"]
    assert res_data["conversation_id"] is not None
    assert res_data["message_id"] is not None
    assert isinstance(res_data["response"], str)
    assert len(res_data["response"]) > 0
    assert "intent" in res_data
    assert "confidence" in res_data
    assert "sources" in res_data
    assert "requires_human_support" in res_data


@pytest.mark.asyncio
async def test_chat_continue_existing_conversation(client: AsyncClient, student_user):
    # First message
    resp1 = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "First question"},
        headers=student_user["headers"],
    )
    assert resp1.status_code == 200
    conv_id = resp1.json()["data"]["conversation_id"]

    # Second message
    resp2 = await client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Follow up question"},
        headers=student_user["headers"],
    )
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["conversation_id"] == conv_id


@pytest.mark.asyncio
async def test_chat_intent_recognition(client: AsyncClient, student_user):
    payload = {
        "conversation_id": None,
        "message": "I forgot my portal password and cannot log in",
    }
    response = await client.post("/api/v1/chat", json=payload, headers=student_user["headers"])
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data["intent"], str)
    assert len(data["intent"]) > 0


@pytest.mark.asyncio
async def test_chat_llm_failure_friendly_fallback(client: AsyncClient, student_user):
    from app.ai import llm_client as llm_mod
    from app.ai.llm_client import _StubRaisingLLMClient

    stub = _StubRaisingLLMClient()

    with patch.object(llm_mod, "_llm_client", stub):
        payload = {
            "conversation_id": None,
            "message": "Any question when LLM is down",
        }
        response = await client.post("/api/v1/chat", json=payload, headers=student_user["headers"])
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        res_data = data["data"]
        # When LLM is unavailable, response generator falls back to:
        # - FALLBACK_MESSAGE ("unable to process"), OR
        # - Low-confidence escalation ("not confident" + requires_human_support=True)
        # Either way, requires_human_support must be True
        assert res_data["requires_human_support"] is True
        assert len(res_data["response"]) > 0


@pytest.mark.asyncio
async def test_chat_unauthenticated(client: AsyncClient):
    response = await client.post("/api/v1/chat", json={"conversation_id": None, "message": "Hello"})
    assert response.status_code == 401

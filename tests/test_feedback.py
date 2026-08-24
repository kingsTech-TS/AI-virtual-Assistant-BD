from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_submit_positive_feedback(client: AsyncClient, student_user):
    # Create conversation and get assistant message
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "How do I register courses?"},
        headers=student_user["headers"],
    )
    assert chat_resp.status_code == 200
    msg_id = chat_resp.json()["data"]["message_id"]

    # Submit positive feedback
    fb_payload = {
        "message_id": msg_id,
        "rating": "positive",
        "comment": "Very clear and helpful steps!",
    }
    fb_resp = await client.post("/api/v1/feedback", json=fb_payload, headers=student_user["headers"])
    assert fb_resp.status_code == 201
    data = fb_resp.json()
    assert data["success"] is True
    assert data["data"]["rating"] == "positive"
    assert data["data"]["message_id"] == msg_id


@pytest.mark.asyncio
async def test_duplicate_feedback_prevention(client: AsyncClient, student_user):
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "When are exams?"},
        headers=student_user["headers"],
    )
    msg_id = chat_resp.json()["data"]["message_id"]

    # First feedback
    fb1 = await client.post(
        "/api/v1/feedback",
        json={"message_id": msg_id, "rating": "positive"},
        headers=student_user["headers"],
    )
    assert fb1.status_code == 201

    # Duplicate feedback -> 409 Conflict
    fb2 = await client.post(
        "/api/v1/feedback",
        json={"message_id": msg_id, "rating": "negative"},
        headers=student_user["headers"],
    )
    assert fb2.status_code == 409
    assert fb2.json()["success"] is False


@pytest.mark.asyncio
async def test_invalid_rating_value(client: AsyncClient, student_user):
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "Hello"},
        headers=student_user["headers"],
    )
    msg_id = chat_resp.json()["data"]["message_id"]

    fb_resp = await client.post(
        "/api/v1/feedback",
        json={"message_id": msg_id, "rating": "neutral"},  # neutral is not allowed
        headers=student_user["headers"],
    )
    assert fb_resp.status_code == 422

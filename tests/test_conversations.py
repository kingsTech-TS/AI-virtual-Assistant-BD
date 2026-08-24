from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_and_get_user_conversations(client: AsyncClient, student_user):
    # Create conversation via chat
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "What is the fee payment deadline?"},
        headers=student_user["headers"],
    )
    assert chat_resp.status_code == 200
    conv_id = chat_resp.json()["data"]["conversation_id"]

    # List conversations
    list_resp = await client.get("/api/v1/chat/conversations", headers=student_user["headers"])
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["success"] is True
    assert len(list_data["items"]) == 1
    assert list_data["items"][0]["id"] == conv_id

    # Get conversation detail
    detail_resp = await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=student_user["headers"])
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["success"] is True
    assert detail_data["data"]["id"] == conv_id
    assert len(detail_data["data"]["messages"]) >= 2  # student + assistant


@pytest.mark.asyncio
async def test_conversation_ownership_protection(client: AsyncClient, student_user, admin_user):
    # Student creates conversation
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "Private conversation"},
        headers=student_user["headers"],
    )
    conv_id = chat_resp.json()["data"]["conversation_id"]

    # Create another student
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Peer Student",
            "email": "peer@demo.institution.edu",
            "password": "Password123!",
            "matric_number": "CSC/2026/099",
        },
    )
    assert reg_resp.status_code == 201
    peer_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "peer@demo.institution.edu", "password": "Password123!"},
    )
    peer_token = peer_login.json()["data"]["access_token"]
    peer_headers = {"Authorization": f"Bearer {peer_token}"}

    # Peer tries to access student's conversation -> 403
    peer_get = await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=peer_headers)
    assert peer_get.status_code == 403

    # Peer tries to delete student's conversation -> 403
    peer_del = await client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=peer_headers)
    assert peer_del.status_code == 403


@pytest.mark.asyncio
async def test_delete_conversation_success(client: AsyncClient, student_user):
    chat_resp = await client.post(
        "/api/v1/chat",
        json={"conversation_id": None, "message": "To be deleted"},
        headers=student_user["headers"],
    )
    conv_id = chat_resp.json()["data"]["conversation_id"]

    del_resp = await client.delete(f"/api/v1/chat/conversations/{conv_id}", headers=student_user["headers"])
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Confirm deletion
    get_resp = await client.get(f"/api/v1/chat/conversations/{conv_id}", headers=student_user["headers"])
    assert get_resp.status_code == 404

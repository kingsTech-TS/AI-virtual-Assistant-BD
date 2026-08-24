from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_student_cannot_create_knowledge(client: AsyncClient, student_user):
    payload = {
        "title": "Unauthorized Knowledge",
        "content": "Content here",
        "category": "general",
    }
    response = await client.post("/api/v1/knowledge", json=payload, headers=student_user["headers"])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_crud_knowledge(client: AsyncClient, admin_user, student_user):
    # Create
    payload = {
        "title": "Official Course Registration Guide",
        "content": "Follow these steps to register courses online.",
        "category": "course_registration",
        "source": "Academic Office",
    }
    create_resp = await client.post("/api/v1/knowledge", json=payload, headers=admin_user["headers"])
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["success"] is True
    doc_id = created_data["data"]["id"]
    assert "embedding" not in created_data["data"]

    # Student can read
    get_resp = await client.get(f"/api/v1/knowledge/{doc_id}", headers=student_user["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["title"] == payload["title"]

    # Update
    update_payload = {"content": "Updated registration procedure steps."}
    update_resp = await client.patch(
        f"/api/v1/knowledge/{doc_id}", json=update_payload, headers=admin_user["headers"]
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["content"] == update_payload["content"]

    # List with category filter
    list_resp = await client.get(
        "/api/v1/knowledge?category=course_registration", headers=student_user["headers"]
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["success"] is True
    assert len(list_data["items"]) >= 1

    # Delete
    del_resp = await client.delete(f"/api/v1/knowledge/{doc_id}", headers=admin_user["headers"])
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_student_cannot_create_faq(client: AsyncClient, student_user):
    payload = {
        "question": "How to register?",
        "answer": "Go to portal",
        "category": "registration",
    }
    response = await client.post("/api/v1/faqs", json=payload, headers=student_user["headers"])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_crud_faq(client: AsyncClient, admin_user, student_user):
    # Create
    payload = {
        "question": "How do I print my examination docket?",
        "answer": "Log in to portal, click Examination, select Docket, and print.",
        "category": "examination",
    }
    create_resp = await client.post("/api/v1/faqs", json=payload, headers=admin_user["headers"])
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["success"] is True
    faq_id = created_data["data"]["id"]

    # Student can read
    get_resp = await client.get(f"/api/v1/faqs/{faq_id}", headers=student_user["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["question"] == payload["question"]

    # Update
    update_payload = {"answer": "Updated answer with new guidelines."}
    update_resp = await client.patch(
        f"/api/v1/faqs/{faq_id}", json=update_payload, headers=admin_user["headers"]
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["answer"] == update_payload["answer"]

    # List FAQs
    list_resp = await client.get("/api/v1/faqs?category=examination", headers=student_user["headers"])
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 1

    # Delete
    del_resp = await client.delete(f"/api/v1/faqs/{faq_id}", headers=admin_user["headers"])
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

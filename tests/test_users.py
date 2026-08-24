from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_users_me(client: AsyncClient, student_user):
    response = await client.get("/api/v1/users/me", headers=student_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == student_user["id"]
    assert data["data"]["email"] == student_user["email"]


@pytest.mark.asyncio
async def test_update_users_me(client: AsyncClient, student_user):
    payload = {"phone": "+1234567890", "name": "Updated Student Name"}
    response = await client.patch("/api/v1/users/me", json=payload, headers=student_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Updated Student Name"
    assert data["data"]["phone"] == "+1234567890"


@pytest.mark.asyncio
async def test_student_cannot_view_other_user(client: AsyncClient, student_user, admin_user):
    response = await client.get(f"/api/v1/users/{admin_user['id']}", headers=student_user["headers"])
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_admin_can_view_any_user(client: AsyncClient, admin_user, student_user):
    response = await client.get(f"/api/v1/users/{student_user['id']}", headers=admin_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == student_user["id"]


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_user, student_user):
    response = await client.get("/api/v1/users", headers=admin_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["items"]) >= 2
    assert "pagination" in data


@pytest.mark.asyncio
async def test_super_admin_change_user_role(client: AsyncClient, super_admin_user, student_user):
    payload = {"role": "staff"}
    response = await client.patch(
        f"/api/v1/admin/users/{student_user['id']}/role",
        json=payload,
        headers=super_admin_user["headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["role"] == "staff"

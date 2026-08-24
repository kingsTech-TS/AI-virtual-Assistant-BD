from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_student_success(client: AsyncClient):
    payload = {
        "name": "Jane Doe",
        "email": "janedoe@demo.institution.edu",
        "password": "Password123!",
        "matric_number": "CSC/2026/042",
        "faculty": "Physical Sciences",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == payload["email"].lower()
    assert data["data"]["role"] == "student"
    assert "password_hash" not in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, student_user):
    payload = {
        "name": "Duplicate Student",
        "email": student_user["email"],
        "password": "Password123!",
        "matric_number": "CSC/2026/999",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_register_duplicate_matric(client: AsyncClient, student_user):
    payload = {
        "name": "Another Student",
        "email": "another@demo.institution.edu",
        "password": "Password123!",
        "matric_number": "CSC/2026/001",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "MATRIC_TAKEN"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, student_user):
    payload = {
        "email": student_user["email"],
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, student_user):
    payload = {
        "email": student_user["email"],
        "password": "WrongPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, student_user):
    response = await client.get("/api/v1/auth/me", headers=student_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["email"] == student_user["email"]
    assert data["data"]["role"] == "student"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient, student_user):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user["email"], "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["data"]["refresh_token"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(client: AsyncClient, student_user):
    forgot_resp = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": student_user["email"]},
    )
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json()["data"]["reset_token"]
    assert reset_token is not None

    reset_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewSecretPassword123!"},
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True

    # Confirm login with new password
    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user["email"], "password": "NewSecretPassword123!"},
    )
    assert login_new.status_code == 200

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_student_create_ticket(client: AsyncClient, student_user, staff_user):
    payload = {
        "subject": "Portal course registration not submitting",
        "description": "When I click submit for departmental approval, the portal displays error code 500.",
        "category": "portal_problem",
        "department_id": staff_user["department_id"],
    }
    response = await client.post("/api/v1/tickets", json=payload, headers=student_user["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    ticket = data["data"]
    assert ticket["ticket_number"].startswith("TCK-")
    assert ticket["status"] == "open"
    assert ticket["subject"] == payload["subject"]


@pytest.mark.asyncio
async def test_ticket_role_scoped_listing(client: AsyncClient, student_user, staff_user, admin_user):
    # Student creates ticket in staff's department
    payload = {
        "subject": "CSC Course Prerequisite Issue",
        "description": "I need a waiver for CSC 301 prerequisites.",
        "category": "departmental_issue",
        "department_id": staff_user["department_id"],
    }
    create_resp = await client.post("/api/v1/tickets", json=payload, headers=student_user["headers"])
    ticket_id = create_resp.json()["data"]["id"]

    # Student list
    student_list = await client.get("/api/v1/tickets", headers=student_user["headers"])
    assert student_list.status_code == 200
    assert any(t["id"] == ticket_id for t in student_list.json()["items"])

    # Staff list (sees it because department matches)
    staff_list = await client.get("/api/v1/tickets", headers=staff_user["headers"])
    assert staff_list.status_code == 200
    assert any(t["id"] == ticket_id for t in staff_list.json()["items"])

    # Admin list (sees all)
    admin_list = await client.get("/api/v1/tickets", headers=admin_user["headers"])
    assert admin_list.status_code == 200
    assert any(t["id"] == ticket_id for t in admin_list.json()["items"])


@pytest.mark.asyncio
async def test_ticket_status_transition_fsm(client: AsyncClient, student_user, staff_user):
    # Create ticket
    payload = {
        "subject": "Examination Docket Signature",
        "description": "My exam docket requires urgent clearance signature.",
        "category": "exam_schedule",
        "department_id": staff_user["department_id"],
    }
    create_resp = await client.post("/api/v1/tickets", json=payload, headers=student_user["headers"])
    ticket_id = create_resp.json()["data"]["id"]

    # Staff moves open -> in_progress
    staff_update = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers=staff_user["headers"],
    )
    assert staff_update.status_code == 200
    assert staff_update.json()["data"]["status"] == "in_progress"

    # Staff moves in_progress -> waiting_for_student
    staff_wait = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "waiting_for_student", "comment": "Please upload a photo of your ID."},
        headers=staff_user["headers"],
    )
    assert staff_wait.status_code == 200
    assert staff_wait.json()["data"]["status"] == "waiting_for_student"

    # Student responds and transitions waiting_for_student -> in_progress
    student_resp = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "in_progress", "comment": "I have uploaded the requested document."},
        headers=student_user["headers"],
    )
    assert student_resp.status_code == 200
    assert student_resp.json()["data"]["status"] == "in_progress"

    # Student cannot resolve ticket directly -> 403
    student_resolve = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=student_user["headers"],
    )
    assert student_resolve.status_code == 403

    # Staff resolves ticket -> 200
    staff_resolve = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved", "comment": "Issue has been resolved."},
        headers=staff_user["headers"],
    )
    assert staff_resolve.status_code == 200
    assert staff_resolve.json()["data"]["status"] == "resolved"

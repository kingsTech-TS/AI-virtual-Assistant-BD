#!/usr/bin/env python3
"""
Role-Based Access Control (RBAC) Test Suite.
Validates authorization rules and boundary separation across Student, Staff, Admin, and Super Admin roles.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from bson import ObjectId

from app.constants.roles import UserRole
from app.constants.statuses import TicketStatus
from app.database.collections import DEPARTMENTS, KNOWLEDGE_BASE, TICKETS, USERS
from app.models.ticket import new_ticket_doc
from app.models.user import new_user_doc
from app.core.security import hash_password, create_access_token


@pytest.mark.asyncio
async def test_1_student_cannot_access_staff_dashboard(client, student_user):
    """1. Student cannot access Staff dashboard."""
    response = await client.get("/api/v1/staff/dashboard", headers=student_user["headers"])
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_2_student_cannot_access_admin_dashboard(client, student_user):
    """2. Student cannot access Admin dashboard."""
    response = await client.get("/api/v1/admin/dashboard", headers=student_user["headers"])
    assert response.status_code == 403
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INSUFFICIENT_ROLE"


@pytest.mark.asyncio
async def test_3_student_cannot_access_another_students_ticket(client, test_db, student_user):
    """3. Student cannot access another student's ticket."""
    other_student_id = ObjectId()
    ticket_doc = new_ticket_doc(
        ticket_number="TCK-99991",
        user_id=other_student_id,
        department_id=None,
        subject="Other student private issue",
        description="Confidential ticket information",
    )
    res = await test_db[TICKETS].insert_one(ticket_doc)
    ticket_id = str(res.inserted_id)

    response = await client.get(f"/api/v1/tickets/{ticket_id}", headers=student_user["headers"])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_4_staff_can_access_assigned_ticket(client, test_db, staff_user):
    """4. Staff can access their assigned tickets."""
    staff_oid = ObjectId(staff_user["id"])
    ticket_doc = new_ticket_doc(
        ticket_number="TCK-99992",
        user_id=ObjectId(),
        department_id=None,  # No dept or different dept
        subject="Assigned inquiry",
        description="Assigned directly to this staff member",
    )
    ticket_doc["assigned_to"] = staff_oid
    res = await test_db[TICKETS].insert_one(ticket_doc)
    ticket_id = str(res.inserted_id)

    response = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=staff_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["ticket_number"] == "TCK-99992"


@pytest.mark.asyncio
async def test_5_staff_can_access_department_ticket(client, test_db, staff_user):
    """5. Staff can access their department's tickets."""
    dept_oid = ObjectId(staff_user["department_id"])
    ticket_doc = new_ticket_doc(
        ticket_number="TCK-99993",
        user_id=ObjectId(),
        department_id=dept_oid,
        subject="Department inquiry",
        description="Question regarding Computer Science courses",
    )
    res = await test_db[TICKETS].insert_one(ticket_doc)
    ticket_id = str(res.inserted_id)

    response = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=staff_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["ticket_number"] == "TCK-99993"


@pytest.mark.asyncio
async def test_6_staff_cannot_access_unrelated_department_ticket(client, test_db, staff_user):
    """6. Staff cannot access unrelated department tickets."""
    other_dept_id = ObjectId()
    ticket_doc = new_ticket_doc(
        ticket_number="TCK-99994",
        user_id=ObjectId(),
        department_id=other_dept_id,
        subject="Physics Lab issue",
        description="Unrelated department ticket",
    )
    ticket_doc["assigned_to"] = None
    res = await test_db[TICKETS].insert_one(ticket_doc)
    ticket_id = str(res.inserted_id)

    response = await client.get(f"/api/v1/staff/tickets/{ticket_id}", headers=staff_user["headers"])
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_7_staff_cannot_modify_roles(client, staff_user, student_user):
    """7. Staff cannot modify roles."""
    response = await client.patch(
        f"/api/v1/admin/users/{student_user['id']}/role",
        headers=staff_user["headers"],
        json={"role": "staff"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_8_staff_cannot_access_admin_apis(client, staff_user):
    """8. Staff cannot access Admin APIs."""
    # Test Admin Dashboard
    dash_resp = await client.get("/api/v1/admin/dashboard", headers=staff_user["headers"])
    assert dash_resp.status_code == 403

    # Test Department Creation
    dept_resp = await client.post(
        "/api/v1/admin/departments",
        headers=staff_user["headers"],
        json={"name": "Forbidden Dept", "code": "FBD"},
    )
    assert dept_resp.status_code == 403

    # Test User Management
    users_resp = await client.get("/api/v1/admin/users", headers=staff_user["headers"])
    assert users_resp.status_code == 403


@pytest.mark.asyncio
async def test_9_admin_can_access_all_tickets(client, test_db, admin_user):
    """9. Admin can access all tickets across all departments."""
    dept1 = ObjectId()
    dept2 = ObjectId()

    t1 = new_ticket_doc("TCK-ADM-01", ObjectId(), dept1, "Subject 1", "Description 1")
    t2 = new_ticket_doc("TCK-ADM-02", ObjectId(), dept2, "Subject 2", "Description 2")
    res1 = await test_db[TICKETS].insert_one(t1)
    res2 = await test_db[TICKETS].insert_one(t2)

    list_resp = await client.get("/api/v1/admin/tickets", headers=admin_user["headers"])
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    ticket_numbers = [item["ticket_number"] for item in items]
    assert "TCK-ADM-01" in ticket_numbers
    assert "TCK-ADM-02" in ticket_numbers

    # Access specific ticket
    detail_resp = await client.get(f"/api/v1/admin/tickets/{res1.inserted_id}", headers=admin_user["headers"])
    assert detail_resp.status_code == 200


@pytest.mark.asyncio
async def test_10_admin_can_manage_knowledge(client, admin_user):
    """10. Admin can manage knowledge base documents."""
    # Create knowledge
    create_resp = await client.post(
        "/api/v1/admin/knowledge",
        headers=admin_user["headers"],
        json={
            "title": "Admin Knowledge Title",
            "content": "This is comprehensive academic knowledge base content.",
            "category": "admission",
            "status": "published",
        },
    )
    assert create_resp.status_code == 201
    doc_id = create_resp.json()["data"]["id"]

    # Update knowledge
    update_resp = await client.patch(
        f"/api/v1/admin/knowledge/{doc_id}",
        headers=admin_user["headers"],
        json={"title": "Updated Admin Knowledge Title"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["title"] == "Updated Admin Knowledge Title"


@pytest.mark.asyncio
async def test_11_admin_can_manage_staff(client, admin_user):
    """11. Admin can manage staff members."""
    # Create staff
    create_resp = await client.post(
        "/api/v1/admin/staff",
        headers=admin_user["headers"],
        json={
            "name": "Dr. Alan Turing",
            "email": "alan.turing@demo.institution.edu",
            "password": "Password123!",
            "staff_id": "STF-2026-042",
            "position": "Senior Lecturer",
            "permissions": ["tickets:manage", "advising"],
        },
    )
    assert create_resp.status_code == 201
    staff_data = create_resp.json()["data"]
    assert staff_data["staff_id"] == "STF-2026-042"
    assert staff_data["position"] == "Senior Lecturer"

    # List staff
    list_resp = await client.get("/api/v1/admin/staff", headers=admin_user["headers"])
    assert list_resp.status_code == 200
    assert any(s["email"] == "alan.turing@demo.institution.edu" for s in list_resp.json()["items"])


@pytest.mark.asyncio
async def test_12_admin_can_manage_departments(client, admin_user):
    """12. Admin can manage departments."""
    # Create department
    create_resp = await client.post(
        "/api/v1/admin/departments",
        headers=admin_user["headers"],
        json={
            "name": "Mechanical Engineering",
            "code": "MEE",
            "faculty": "Engineering",
            "description": "Department of Mechanical Engineering",
            "support_email": "mee-support@demo.institution.edu",
        },
    )
    assert create_resp.status_code == 201
    dept_id = create_resp.json()["data"]["id"]

    # Update department
    update_resp = await client.patch(
        f"/api/v1/admin/departments/{dept_id}",
        headers=admin_user["headers"],
        json={"description": "Updated Mechanical Engineering Description"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["description"] == "Updated Mechanical Engineering Description"


@pytest.mark.asyncio
async def test_13_super_admin_can_manage_admin_accounts(client, test_db, super_admin_user, admin_user, student_user):
    """13. Super Admin can manage Admin accounts."""
    # Standard Admin CANNOT call role change endpoint (restricted to super_admin)
    fail_resp = await client.patch(
        f"/api/v1/admin/users/{student_user['id']}/role",
        headers=admin_user["headers"],
        json={"role": "super_admin"},
    )
    assert fail_resp.status_code == 403

    # Super Admin CAN call role change endpoint to upgrade user
    role_resp = await client.patch(
        f"/api/v1/admin/users/{student_user['id']}/role",
        headers=super_admin_user["headers"],
        json={"role": "admin"},
    )
    assert role_resp.status_code == 200
    assert role_resp.json()["data"]["role"] == "admin"


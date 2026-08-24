from __future__ import annotations

from app.constants.roles import UserRole

DEFAULT_USER_FIELDS = {
    "_id": 1,
    "name": 1,
    "email": 1,
    "matric_number": 1,
    "staff_id": 1,
    "department_id": 1,
    "faculty": 1,
    "phone": 1,
    "position": 1,
    "permissions": 1,
    "role": 1,
    "is_active": 1,
    "created_at": 1,
    "updated_at": 1,
}

USER_PRIVATE_FIELDS = {"password_hash", "refresh_tokens"}


def user_to_dict(user_doc, include_secrets: bool = False) -> dict:
    if not user_doc:
        return {}
    doc = dict(user_doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
    if "department_id" in doc and doc["department_id"]:
        doc["department_id"] = str(doc["department_id"])
    else:
        doc["department_id"] = None
    if "permissions" not in doc or doc["permissions"] is None:
        doc["permissions"] = []
    if not include_secrets:
        for f in USER_PRIVATE_FIELDS:
            doc.pop(f, None)
    return doc


def new_user_doc(
    name: str,
    email: str,
    password_hash: str,
    role: str = UserRole.STUDENT.value if hasattr(UserRole.STUDENT, "value") else "student",
    matric_number: str | None = None,
    staff_id: str | None = None,
    department_id=None,
    faculty: str | None = None,
    phone: str | None = None,
    position: str | None = None,
    permissions: list | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    now = utcnow()
    doc = {
        "name": name,
        "email": email.lower() if email else email,
        "password_hash": password_hash,
        "role": role.value if hasattr(role, "value") else role,
        "is_active": True,
        "refresh_tokens": [],
        "created_at": now,
        "updated_at": now,
    }
    if matric_number:
        doc["matric_number"] = matric_number
    if staff_id:
        doc["staff_id"] = staff_id
    if department_id:
        doc["department_id"] = department_id
    if faculty:
        doc["faculty"] = faculty
    if phone:
        doc["phone"] = phone
    if position:
        doc["position"] = position
    if permissions is not None:
        doc["permissions"] = list(permissions)
    else:
        doc["permissions"] = []
    return doc

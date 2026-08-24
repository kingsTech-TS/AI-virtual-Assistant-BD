from __future__ import annotations


def new_department_doc(
    name: str,
    code: str,
    faculty: str | None = None,
    description: str | None = None,
    support_email: str | None = None,
) -> dict:
    from app.utils.helpers import utcnow
    return {
        "name": name,
        "code": code.upper() if code else code,
        "faculty": faculty,
        "description": description,
        "support_email": support_email,
        "is_active": True,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }


def department_to_dict(doc) -> dict:
    if not doc:
        return {}
    d = dict(doc)
    d["id"] = str(d["_id"])
    d["_id"] = str(d["_id"])
    return d

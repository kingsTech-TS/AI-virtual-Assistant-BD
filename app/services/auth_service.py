from __future__ import annotations

from typing import Any, Dict

from bson import ObjectId

from app.constants.roles import UserRole
from app.core.config import settings
from app.core.exceptions import BadRequest, Conflict, NotFound, Unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.collections import USERS
from app.models.user import new_user_doc, user_to_dict
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import audit_action
from app.utils.helpers import utcnow
from app.utils.ids import to_obj_id


async def register(db, data: RegisterRequest) -> Dict[str, Any]:
    existing = await db[USERS].find_one({"email": data.email.lower()})
    if existing:
        raise Conflict(message="A user with this email already exists", code="EMAIL_TAKEN")
    if getattr(data, "matric_number", None):
        dup = await db[USERS].find_one({"matric_number": data.matric_number})
        if dup:
            raise Conflict(message="Matric number already registered", code="MATRIC_TAKEN")
    doc = new_user_doc(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.STUDENT.value,
        matric_number=getattr(data, "matric_number", None),
        department_id=to_obj_id(getattr(data, "department_id", None)),
        faculty=getattr(data, "faculty", None),
        phone=getattr(data, "phone", None),
    )
    result = await db[USERS].insert_one(doc)
    doc["_id"] = result.inserted_id
    return user_to_dict(doc)


async def login(db, data: LoginRequest):
    user = await db[USERS].find_one({"email": data.email.lower()})
    if not user:
        raise Unauthorized(message="Invalid email or password", code="INVALID_CREDENTIALS")
    if not user.get("is_active", True):
        raise Unauthorized(message="Account is disabled", code="USER_DISABLED")
    if not verify_password(data.password, user.get("password_hash") or ""):
        raise Unauthorized(message="Invalid email or password", code="INVALID_CREDENTIALS")
    uid = user["_id"]
    role = user.get("role", UserRole.STUDENT.value)
    access_token = create_access_token(subject=uid, role=role)
    refresh_token, jti = create_refresh_token(subject=uid)
    await db[USERS].update_one(
        {"_id": uid},
        {
            "$set": {"updated_at": utcnow()},
            "$push": {"refresh_tokens": {"$each": [jti], "$slice": -10}},
        },
    )
    from app.schemas.auth import TokenResponse
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def refresh(db, refresh_token: str):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise Unauthorized(message="Invalid refresh token", code="TOKEN_TYPE_INVALID")
    sub = payload.get("sub")
    if not sub:
        raise Unauthorized(message="Invalid token subject", code="TOKEN_SUB_MISSING")
    oid = to_obj_id(sub)
    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise Unauthorized(message="User no longer exists", code="USER_NOT_FOUND")
    if not user.get("is_active", True):
        raise Unauthorized(message="Account disabled", code="USER_DISABLED")
    jti = payload.get("jti")
    active_tokens = user.get("refresh_tokens") or []
    if not isinstance(active_tokens, list):
        active_tokens = []
    if jti and active_tokens and jti not in active_tokens:
        raise Unauthorized(message="Refresh token has been revoked", code="TOKEN_REVOKED")

    new_access = create_access_token(subject=oid, role=user.get("role", UserRole.STUDENT.value))
    new_refresh, new_jti = create_refresh_token(subject=oid)

    updated_tokens = [t for t in active_tokens if t != jti]
    updated_tokens.append(new_jti)
    updated_tokens = updated_tokens[-10:]

    await db[USERS].update_one(
        {"_id": oid},
        {
            "$set": {
                "updated_at": utcnow(),
                "refresh_tokens": updated_tokens,
            }
        },
    )
    from app.schemas.auth import TokenResponse
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


async def logout(db, current_user: Dict[str, Any], token_jti_or_str: str | None = None) -> Dict[str, Any]:
    oid = to_obj_id(current_user.get("_id"))
    update: Dict[str, Any] = {"$set": {"updated_at": utcnow()}}
    jti = None
    if token_jti_or_str:
        try:
            payload = decode_token(token_jti_or_str)
            if payload.get("type") == "refresh":
                jti = payload.get("jti")
        except Exception:
            pass
    if jti:
        update["$pull"] = {"refresh_tokens": jti}
    else:
        update["$set"] = {"refresh_tokens": []}
    await db[USERS].update_one({"_id": oid}, update)
    await audit_action(
        db,
        user_id=oid,
        action="logout",
        resource_type="user",
        resource_id=oid,
        metadata={"method": "refresh_revocation"},
    )
    return {"message": "Logged out successfully"}


async def forgot_password(db, email: str) -> Dict[str, Any]:
    user = await db[USERS].find_one({"email": email.lower()})
    if not user:
        return {
            "reset_token": create_reset_token(subject="unknown"),
            "message": "If this email is registered, a password reset link has been generated.",
        }
    reset_token = create_reset_token(subject=user["_id"])
    return {
        "reset_token": reset_token,
        "message": "Password reset token generated (dev view). In production, this would be emailed only.",
    }


async def reset_password(db, reset_token: str, new_password: str) -> Dict[str, Any]:
    payload = decode_token(reset_token)
    if payload.get("type") != "reset":
        raise BadRequest(message="Invalid or expired reset token", code="TOKEN_TYPE_INVALID")
    sub = payload.get("sub")
    oid = to_obj_id(sub)
    if not oid:
        raise BadRequest(message="Invalid reset token", code="TOKEN_SUBJECT_INVALID")
    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    new_hash = hash_password(new_password)
    await db[USERS].update_one(
        {"_id": oid},
        {
            "$set": {
                "password_hash": new_hash,
                "refresh_tokens": [],
                "updated_at": utcnow(),
            }
        },
    )
    await audit_action(
        db,
        user_id=oid,
        action="password_reset",
        resource_type="user",
        resource_id=oid,
    )
    return {"message": "Password reset successfully"}

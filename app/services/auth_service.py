from __future__ import annotations

from datetime import timedelta
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
from app.database.collections import PASSWORD_RESET_TOKENS, USERS
from app.models.user import new_user_doc, user_to_dict
from app.schemas.auth import LoginRequest, RegisterRequest, StaffRegisterRequest
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


async def register_staff(db, data: StaffRegisterRequest) -> Dict[str, Any]:
    existing = await db[USERS].find_one({"email": data.email.lower()})
    if existing:
        raise Conflict(message="A user with this email already exists", code="EMAIL_TAKEN")
    if getattr(data, "staff_id", None):
        dup = await db[USERS].find_one({"staff_id": data.staff_id})
        if dup:
            raise Conflict(message="Staff ID already registered", code="STAFF_ID_TAKEN")
    doc = new_user_doc(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.STAFF.value,
        staff_id=getattr(data, "staff_id", None),
        department_id=to_obj_id(getattr(data, "department_id", None)),
        faculty=getattr(data, "faculty", None),
        phone=getattr(data, "phone", None),
        position=getattr(data, "position", None),
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
            "message": "If this email is registered, a password reset link has been sent.",
        }

    user_id = to_obj_id(user["_id"])
    now = utcnow()
    reset_token, jti = create_reset_token(subject=user_id)
    expires_at = now + timedelta(minutes=60)

    await db[PASSWORD_RESET_TOKENS].update_many(
        {"user_id": user_id, "is_used": False, "is_invalidated": False},
        {"$set": {"is_invalidated": True, "invalidated_at": now}},
    )

    token_doc = {
        "jti": jti,
        "user_id": user_id,
        "email": email.lower(),
        "role": user.get("role"),
        "expires_at": expires_at,
        "is_used": False,
        "is_invalidated": False,
        "created_at": now,
    }
    await db[PASSWORD_RESET_TOKENS].insert_one(token_doc)

    try:
        from app.services.email_service import send_password_reset_email
        await send_password_reset_email(email, reset_token, user.get("name", ""))
    except Exception:
        pass

    response: Dict[str, Any] = {
        "message": "If this email is registered, a password reset link has been sent.",
    }
    if settings.APP_ENV in ("development", "testing") or settings.DEBUG:
        response["reset_token"] = reset_token
        response["reset_url"] = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    return response


async def reset_password(db, reset_token: str, new_password: str) -> Dict[str, Any]:
    payload = decode_token(reset_token)
    if payload.get("type") != "reset":
        raise BadRequest(message="Invalid or expired reset token", code="TOKEN_TYPE_INVALID")
    sub = payload.get("sub")
    oid = to_obj_id(sub)
    if not oid:
        raise BadRequest(message="Invalid reset token", code="TOKEN_SUBJECT_INVALID")

    jti = payload.get("jti")
    token_doc = None
    if jti:
        token_doc = await db[PASSWORD_RESET_TOKENS].find_one({"jti": jti})

    if token_doc:
        if token_doc.get("is_used"):
            raise BadRequest(message="Reset token has already been used", code="TOKEN_USED")
        if token_doc.get("is_invalidated"):
            raise BadRequest(message="Reset token has been invalidated", code="TOKEN_INVALIDATED")
        expires_at = token_doc.get("expires_at")
        if expires_at and expires_at < utcnow():
            raise BadRequest(message="Reset token has expired", code="TOKEN_EXPIRED")
        if token_doc.get("user_id") != oid:
            raise BadRequest(message="Invalid reset token", code="TOKEN_SUBJECT_MISMATCH")
    else:
        raise BadRequest(message="Invalid or expired reset token", code="TOKEN_NOT_FOUND")

    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise NotFound(message="User not found", code="USER_NOT_FOUND")
    if not user.get("is_active", True):
        raise BadRequest(message="Account is disabled", code="USER_DISABLED")

    new_hash = hash_password(new_password)
    now = utcnow()

    await db[PASSWORD_RESET_TOKENS].update_one(
        {"jti": jti},
        {"$set": {"is_used": True, "used_at": now}},
    )

    await db[USERS].update_one(
        {"_id": oid},
        {
            "$set": {
                "password_hash": new_hash,
                "refresh_tokens": [],
                "updated_at": now,
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

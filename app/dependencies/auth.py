from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer

from app.constants.roles import UserRole, has_min_role
from app.core.exceptions import Forbidden, Unauthorized
from app.core.security import decode_token
from app.database.collections import USERS
from app.dependencies.database import get_db
from app.models.user import user_to_dict
from app.utils.ids import to_obj_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Dict[str, Any]:
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise Unauthorized(message="Authentication credentials were not provided", code="AUTH_MISSING")

    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != "access":
        raise Unauthorized(message="Invalid token type", code="TOKEN_TYPE_INVALID")

    user_id = payload.get("sub")
    if not user_id:
        raise Unauthorized(message="Token missing subject", code="TOKEN_MALFORMED")

    oid = to_obj_id(user_id)
    if not oid:
        raise Unauthorized(message="Invalid user id in token", code="TOKEN_INVALID_SUBJECT")

    user = await db[USERS].find_one({"_id": oid})
    if not user:
        raise Unauthorized(message="User no longer exists", code="USER_NOT_FOUND")
    if not user.get("is_active", True):
        raise Forbidden(message="User account is disabled", code="USER_DISABLED")

    jti = payload.get("jti")
    if jti:
        active_tokens = user.get("refresh_tokens") or []
        pass

    user_dict = user_to_dict(user, include_secrets=False)
    user_dict["_jti"] = jti
    user_dict["_token"] = token
    return user_dict


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    if not current_user.get("is_active", True):
        raise Forbidden(message="Inactive user", code="USER_INACTIVE")
    return current_user


def require_roles(*roles: UserRole | str):
    role_strs = [r.value if isinstance(r, UserRole) else r for r in roles]

    async def checker(
        current_user: Dict[str, Any] = Depends(get_current_active_user),
    ) -> Dict[str, Any]:
        user_role = current_user.get("role")
        ok = any(has_min_role(user_role, r) for r in role_strs)
        if not ok:
            raise Forbidden(
                message=f"Insufficient permissions. Required one of: {role_strs}",
                code="INSUFFICIENT_ROLE",
            )
        return current_user

    return checker


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Optional[Dict[str, Any]]:
    try:
        return await get_current_user(request=request, token=token, authorization=authorization, db=db)
    except Exception:
        return None

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_RESET = "reset"
TOKEN_TYPE_FIELD = "type"
USER_ID_CLAIM = "sub"
ROLE_CLAIM = "role"
EXPIRE_CLAIM = "exp"
ISSUED_AT_CLAIM = "iat"
JTI_CLAIM = "jti"


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def _create_token(
    token_type: str,
    subject: Any,
    expires_delta: timedelta,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    jti = str(uuid.uuid4())
    sub_str = str(subject) if subject else ""
    to_encode: Dict[str, Any] = {
        USER_ID_CLAIM: sub_str,
        TOKEN_TYPE_FIELD: token_type,
        ISSUED_AT_CLAIM: datetime.now(timezone.utc),
        JTI_CLAIM: jti,
    }
    if extra_claims:
        to_encode.update(extra_claims)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode[EXPIRE_CLAIM] = expire
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt, jti


def create_access_token(
    subject: Any,
    role: Optional[str] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    claims = extra_claims or {}
    if role is not None:
        claims[ROLE_CLAIM] = role
    token, _ = _create_token(
        token_type=TOKEN_TYPE_ACCESS,
        subject=subject,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims=claims,
    )
    return token


def create_refresh_token(
    subject: Any,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    return _create_token(
        token_type=TOKEN_TYPE_REFRESH,
        subject=subject,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims=extra_claims,
    )


def create_reset_token(
    subject: Any,
    expires_minutes: int = 60,
) -> Tuple[str, str]:
    return _create_token(
        token_type=TOKEN_TYPE_RESET,
        subject=subject,
        expires_delta=timedelta(minutes=expires_minutes),
    )


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return {}

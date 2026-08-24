import re
from typing import Any, Dict, List, Optional

from email_validator import (
    EmailNotValidError,
    EmailSyntaxError,
    EmailUndeliverableError,
    validate_email as _validate_email,
)

from app.core.exceptions import BadRequest

_MONGO_INJECTION_PATTERNS: List[str] = [
    r"\$where",
    r"\$expr",
    r"\$regex.*function",
    r"\$accumulator",
    r"\$function",
    r"\$jsonSchema.*\$where",
    r"\$map.*function",
]

_MONGO_STRING_INJECTION_RE = re.compile(
    r"(\$where|\$expr|\$function|\$accumulator)", re.IGNORECASE
)

_MATRIC_NUMBER_RE = re.compile(r"^[A-Za-z0-9]{3,20}$")


def validate_email(email: str) -> str:
    if not email or not isinstance(email, str):
        raise BadRequest("Email address is required.")
    try:
        normalized = _validate_email(email.strip(), check_deliverability=False)
        return normalized.normalized
    except (EmailSyntaxError, EmailUndeliverableError, EmailNotValidError) as exc:
        raise BadRequest(f"Invalid email address: {exc}")


def validate_matric_number(matric_number: str) -> bool:
    if not matric_number or not isinstance(matric_number, str):
        return False
    return bool(_MATRIC_NUMBER_RE.match(matric_number.strip()))


def _scan_value(value: Any, depth: int = 0) -> bool:
    if depth > 10:
        return True
    if isinstance(value, str):
        if _MONGO_STRING_INJECTION_RE.search(value):
            return False
        return True
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and k.startswith("$"):
                return False
            if not _scan_value(v, depth + 1):
                return False
        return True
    if isinstance(value, (list, tuple)):
        for item in value:
            if not _scan_value(item, depth + 1):
                return False
        return True
    return True


def is_safe_query_string(query: Dict[str, Any]) -> bool:
    if not isinstance(query, dict):
        return False
    return _scan_value(query)


def ensure_safe_query(query: Dict[str, Any]) -> Dict[str, Any]:
    if not is_safe_query_string(query):
        raise BadRequest("Query contains potentially unsafe patterns.")
    return query


_SANITIZE_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
_MULTI_SPACE_PATTERN = re.compile(r"\s+")


def sanitize_string(value: str, strip_html: bool = True) -> str:
    if not isinstance(value, str):
        return str(value) if value is not None else ""
    result = _SANITIZE_PATTERN.sub("", value)
    if strip_html:
        result = _HTML_TAG_PATTERN.sub("", result)
    result = _MULTI_SPACE_PATTERN.sub(" ", result).strip()
    return result

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utcnow().isoformat()


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        if len(local) > 1:
            masked_local = local[0] + "*" * (len(local) - 1)
        else:
            masked_local = local[0] if local else "*"
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    domain_parts = domain.split(".")
    if len(domain_parts) > 1:
        tld = "." + ".".join(domain_parts[1:])
        first_part = domain_parts[0]
        masked_domain = first_part[:1] + "*" * max(1, len(first_part) - 1) + tld
    else:
        masked_domain = "*" * len(domain)
    return f"{masked_local}@{masked_domain}"


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


_ticket_counter: Dict[str, int] = {}


def generate_ticket_number(start_from: Optional[int] = None) -> str:
    start = start_from if start_from is not None else settings.TICKET_START_NUMBER
    key = "ticket_seq"
    current = _ticket_counter.get(key, start)
    next_num = current
    _ticket_counter[key] = current + 1
    return f"TCK-{next_num}"


def safe_ticket_reset(start_from: Optional[int] = None) -> None:
    start = start_from if start_from is not None else settings.TICKET_START_NUMBER
    _ticket_counter["ticket_seq"] = start

import json
import logging
import sys
import time
import uuid
from typing import Any, Dict, List, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

SECRET_KEY_PATTERNS: Tuple[str, ...] = (
    "password",
    "secret",
    "key",
    "token",
    "hash",
    "uri",
    "authorization",
    "jwt",
)

REDACTED = "***REDACTED***"


class SecretScrubbingFilter(logging.Filter):
    def _scrub_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return REDACTED
        if isinstance(value, dict):
            return self._scrub_dict(value)
        if isinstance(value, list):
            return [self._scrub_item(v) for v in value]
        return value

    def _scrub_item(self, item: Any) -> Any:
        if isinstance(item, dict):
            return self._scrub_dict(item)
        if isinstance(item, list):
            return [self._scrub_item(i) for i in item]
        return item

    def _scrub_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        scrubbed: Dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(pattern in key_lower for pattern in SECRET_KEY_PATTERNS):
                scrubbed[key] = REDACTED
            else:
                scrubbed[key] = self._scrub_item(value)
        return scrubbed

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, dict):
            record.args = self._scrub_dict(args)
        elif isinstance(args, tuple):
            scrubbed_list: List[Any] = []
            for arg in args:
                if isinstance(arg, dict):
                    scrubbed_list.append(self._scrub_dict(arg))
                else:
                    scrubbed_list.append(arg)
            record.args = tuple(scrubbed_list)
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry)


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers: List[logging.Handler] = []

    console_handler = logging.StreamHandler(sys.stdout)
    if settings.APP_ENV.lower() == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        simple_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(simple_fmt)
    console_handler.addFilter(SecretScrubbingFilter())
    handlers.append(console_handler)

    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,
    )

    for noisy_logger in ("uvicorn.access", "uvicorn", "motor"):
        logging.getLogger(noisy_logger).setLevel(max(log_level, logging.WARNING))


logger = logging.getLogger("app")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        request.state.request_id = request_id

        log_extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }

        try:
            response = await call_next(request)
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_extra["status_code"] = response.status_code
            log_extra["duration_ms"] = duration_ms

            if response.status_code >= 500:
                logger.error("Request failed", extra=log_extra)
            elif response.status_code >= 400:
                logger.warning("Request error", extra=log_extra)
            else:
                logger.info("Request completed", extra=log_extra)

            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_extra["status_code"] = 500
            log_extra["duration_ms"] = duration_ms
            logger.exception(f"Unhandled exception: {exc}", extra=log_extra)
            raise

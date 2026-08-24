from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFound(AppException):
    def __init__(
        self,
        message: str = "The requested resource was not found.",
        code: str = "RESOURCE_NOT_FOUND",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class Unauthorized(AppException):
    def __init__(
        self,
        message: str = "Authentication required.",
        code: str = "UNAUTHORIZED",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class Forbidden(AppException):
    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class BadRequest(AppException):
    def __init__(
        self,
        message: str = "Invalid request.",
        code: str = "BAD_REQUEST",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ServiceUnavailable(AppException):
    def __init__(
        self,
        message: str = "Service is currently unavailable.",
        code: str = "SERVICE_UNAVAILABLE",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class Conflict(AppException):
    def __init__(
        self,
        message: str = "Resource conflict.",
        code: str = "CONFLICT",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


class LLMUnavailableError(ServiceUnavailable):
    def __init__(
        self,
        message: str = "AI service is temporarily unavailable. Please try again later or create a support ticket.",
        code: str = "LLM_UNAVAILABLE",
    ) -> None:
        super().__init__(message=message, code=code)


def _error_response(code: str, message: str) -> Dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(exc.code, exc.message),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    messages = []
    for err in errors:
        loc = " -> ".join(str(part) for part in err.get("loc", []))
        msg = err.get("msg", "")
        if loc:
            messages.append(f"{loc}: {msg}")
        else:
            messages.append(msg)
    combined = "; ".join(messages) if messages else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_response("VALIDATION_ERROR", combined),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    code_map = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
        status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
        status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response(code, message),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again later.",
        ),
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

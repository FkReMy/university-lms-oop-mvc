"""
app/utils/exceptions.py
Centralized, Beautiful, Production-Ready Custom Exceptions
Used across entire LMS for consistent error handling
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    request_validation_exception_handler,
    http_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CUSTOM APPLICATION EXCEPTIONS (Business Logic)
# =============================================================================

class AppException(HTTPException):
    """Base class for all custom exceptions"""
    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        headers: Optional[Dict[str, str]] = None
    ):
        self.code = code
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class UnauthorizedException(AppException):
    """401 - Invalid credentials or token"""
    def __init__(self, detail: str = "Invalid email or password"):
        super().__init__(401, "UNAUTHORIZED", detail)


class ForbiddenException(AppException):
    """403 - User lacks permission"""
    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(403, "FORBIDDEN", detail)


class NotFoundException(AppException):
    """404 - Resource not found"""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(404, "NOT_FOUND", detail)


class ConflictException(AppException):
    """409 - Resource conflict (already exists, etc.)"""
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(409, "CONFLICT", detail)


class BadRequestException(AppException):
    """400 - Client error"""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(400, "BAD_REQUEST", detail)


class UnprocessableEntityException(AppException):
    """422 - Validation failed"""
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(422, "UNPROCESSABLE_ENTITY", detail)


class TooManyRequestsException(AppException):
    """429 - Rate limited"""
    def __init__(self, detail: str = "Too many requests"):
        super().__init__(429, "TOO_MANY_REQUESTS", detail)


class InternalServerErrorException(AppException):
    """500 - Server error"""
    def __init__(self, detail: str = "Internal server error"):
        super().__init__(500, "INTERNAL_ERROR", detail)


# =============================================================================
# GLOBAL EXCEPTION HANDLER (Beautiful, Consistent Responses)
# =============================================================================

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all custom AppException errors"""
    response = {
        "success": False,
        "error": {
            "code": exc.code,
            "detail": exc.detail,
            "path": str(request.url),
            "method": request.method,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    }
    
    logger.warning(f"{exc.code} - {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers=exc.headers
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Beautiful 422 validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    response = {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "detail": "Request validation failed",
            "errors": errors,
            "path": str(request.url),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    }

    logger.warning(f"Validation error: {errors} - {request.url}")
    return JSONResponse(status_code=422, content=response)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected errors (never expose stack trace in prod)"""
    logger.error(f"Unhandled exception: {exc} - {request.url}", exc_info=True)

    response = {
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z"
        }
    }

    return JSONResponse(status_code=500, content=response)


# =============================================================================
# REGISTER IN main.py LIKE THIS:
# =============================================================================
"""
# In your main.py or app entrypoint:

from app.utils.exceptions import (
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    AppException
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
"""
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.logger import logger


class ApiException(Exception):
    """Custom exception for explicit API errors."""

    def __init__(self, status_code: int, detail: str) -> None:
        """Initialize an API exception with status code and message."""
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for the FastAPI app."""

    @app.exception_handler(ApiException)
    async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
        """Handle custom API exceptions with normalized payload."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors in a consistent format."""
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": "Validation error.", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions and hide internal details from clients."""
        logger.exception("Unhandled exception: {}", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error."},
        )

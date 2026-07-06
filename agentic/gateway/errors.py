"""Typed exception handlers registered on the FastAPI app."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422: Pydantic request body validation failed."""
    logger.warning(
        "validation error req_id=%s path=%s errors=%s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
        exc.errors(),
    )
    # Pydantic v2 errors include field location and message. Surface them
    # so the Go backend can log which field was wrong without exposing
    # any server internals.
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """400: Caller passed invalid data caught at the service boundary."""
    logger.warning(
        "bad request req_id=%s path=%s: %s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


async def runtime_error_handler(
    request: Request, exc: RuntimeError
) -> JSONResponse:
    """503: Service dependency unavailable (Postgres, Neo4j, graph not built)."""
    logger.error(
        "service unavailable req_id=%s path=%s: %s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Agentic service temporarily unavailable."},
    )


async def unhandled_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """500: Unexpected error. Log fully, return safe message."""
    logger.exception(
        "unhandled error req_id=%s path=%s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )

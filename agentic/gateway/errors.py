"""buat registerini"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """validasi, error"""
    logger.warning(
        "validation error req_id=%s path=%s errors=%s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
        exc.errors(),
    )
    # log "go backend
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """parse"""
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
    """skip"""
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
    """log err, return safe msg"""
    logger.exception(
        "unhandled error req_id=%s path=%s",
        getattr(request.state, "request_id", "-"),
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )

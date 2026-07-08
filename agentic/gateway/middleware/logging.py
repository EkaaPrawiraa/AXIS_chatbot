"""req id" "log timing"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from agentic.gateway.monitoring import observe_http_request


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """ekstrak id permintaan"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id

        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        observe_http_request(
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s %d %dms req_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

"""mgmt"""

from __future__ import annotations

import hmac
from collections.abc import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class PrivateKeyMiddleware(BaseHTTPMiddleware):
    """send req"""

    def __init__(
        self,
        app,
        *,
        private_key: str | None,
        header_name: str = "X-Agentic-Private-Key",
        public_paths: Iterable[str] = ("/health",),
    ) -> None:
        super().__init__(app)
        self.private_key = private_key or ""
        self.header_name = header_name
        self.public_paths = tuple(public_paths)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        if self._is_public(request.url.path):
            return await call_next(request)

        if not self.private_key:
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Agentic gateway private key is not configured."
                },
            )

        provided = request.headers.get(self.header_name, "")
        if not hmac.compare_digest(provided, self.private_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid agentic gateway private key."},
            )

        return await call_next(request)

    def _is_public(self, path: str) -> bool:
        return any(path == item or path.startswith(f"{item}/") for item in self.public_paths)
"""Production entry point for the Agentic gateway."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_local_env() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    # .env.local loads first so its values take precedence (kept stable
    # for local dev/testing while .env is edited for deployment prep).
    _load_env_file(base_dir / ".env.local")
    _load_env_file(base_dir / ".env")


_load_local_env()

from agentic.gateway.app import create_app


logger = logging.getLogger(__name__)

# Module-level app object. Uvicorn/gunicorn import this directly.
app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("AGENTIC_HOST", "0.0.0.0")
    port = int(os.getenv("AGENTIC_PORT", "8000"))
    log_level = os.getenv("AGENTIC_LOG_LEVEL", "info").lower()
    reload = os.getenv("AGENTIC_RELOAD", "").lower() in ("1", "true", "yes")

    logger.info(
        "Starting agentic gateway on %s:%d log_level=%s reload=%s",
        host,
        port,
        log_level,
        reload,
    )
    uvicorn.run(
        "agentic.server.main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
    )

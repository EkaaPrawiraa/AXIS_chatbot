"""fastapi init"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from agentic.agent.session.activity_repo import PostgresSessionActivityRepository
from agentic.agent.session.finalizer_factory import build_session_finalizer
from agentic.agent.session.sweeper import SessionSweeper, SweeperConfig
from agentic.gateway.controller.chat import register_chat_routes
from agentic.gateway.controller.memory import register_memory_routes
from agentic.gateway.errors import (
    runtime_error_handler,
    unhandled_error_handler,
    validation_error_handler,
    value_error_handler,
)
from agentic.gateway.middleware.logging import RequestLoggingMiddleware
from agentic.gateway.middleware.private_key import PrivateKeyMiddleware
from agentic.gateway.monitoring import snapshot as metrics_snapshot
from agentic.gateway.service.chat_graph import ChatGraphService


logger = logging.getLogger(__name__)
startup_logger = logging.getLogger("uvicorn.error")


def _seconds_until_next_decay_run(hour_utc: int = 2) -> float:
    """get utc run"""
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


async def _memory_decay_loop() -> None:
    """run decay fail daily."""
    while True:
        wait_s = _seconds_until_next_decay_run(hour_utc=2)
        logger.info(
            "memory decay: next run scheduled in %.0f minutes (02:00 UTC)",
            wait_s / 60,
        )
        await asyncio.sleep(wait_s)
        try:
            from agentic.memory.knowledge_graph.kg_algorithm.decay import (
                run_memory_decay,
            )

            result = await run_memory_decay()
            logger.info(
                "memory decay: complete, halved=%d archived=%d",
                result.get("halved", 0),
                result.get("archived", 0),
            )
        except Exception as exc:
            logger.error("memory decay: run failed (will retry tomorrow): %s", exc)


async def _pgvector_sync_loop() -> None:
    """retry, unsync, kg, emb"""
    interval_s = float(os.getenv("PGVECTOR_SYNC_INTERVAL_SECONDS", "300"))
    batch_size = int(os.getenv("PGVECTOR_SYNC_BATCH_SIZE", "100"))
    while True:
        await asyncio.sleep(max(30.0, interval_s))
        try:
            from agentic.memory.cross_store_sync import sweep_unsynced

            result = await sweep_unsynced(batch_size=batch_size)
            scanned = sum(v.get("scanned", 0) for v in result.values())
            synced = sum(v.get("synced", 0) for v in result.values())
            failed = sum(v.get("failed", 0) for v in result.values())
            if scanned:
                logger.info(
                    "pgvector sync: scanned=%d synced=%d failed=%d",
                    scanned,
                    synced,
                    failed,
                )
        except Exception as exc:
            logger.error("pgvector sync: run failed (will retry): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """start serv & bg woks"""
    startup_logger.info(
        "agentic gateway starting up; graph_state_log=%s",
        os.getenv("AXIS_GRAPH_STATE_LOG", "").strip() or "off",
    )
    service = ChatGraphService()
    try:
        await service._get_graph()
        logger.info("agentic gateway ready")
    except Exception as exc:
        logger.error("graph compilation failed at startup: %s", exc)

    app.state.chat_service = service

    decay_enabled = os.getenv("MEMORY_DECAY_ENABLED", "1") not in ("0", "false", "off")
    decay_task: asyncio.Task | None = None
    if decay_enabled:
        decay_task = asyncio.create_task(
            _memory_decay_loop(), name="memory_decay_scheduler"
        )
        logger.info("memory decay scheduler started (runs daily at 02:00 UTC)")
    else:
        logger.info("memory decay scheduler disabled (MEMORY_DECAY_ENABLED=0)")

    pgvector_sync_task: asyncio.Task | None = None
    pgvector_sync_enabled = (
        os.getenv("PGVECTOR_SYNC_ENABLED", "1") not in ("0", "false", "off")
    )
    if pgvector_sync_enabled:
        pgvector_sync_task = asyncio.create_task(
            _pgvector_sync_loop(), name="pgvector_sync_scheduler"
        )
        logger.info(
            "pgvector sync scheduler started (interval=%ss, batch=%s)",
            os.getenv("PGVECTOR_SYNC_INTERVAL_SECONDS", "300"),
            os.getenv("PGVECTOR_SYNC_BATCH_SIZE", "100"),
        )
    else:
        logger.info("pgvector sync scheduler disabled (PGVECTOR_SYNC_ENABLED=0)")

    sweeper_task: asyncio.Task | None = None
    sweeper: SessionSweeper | None = None
    sweeper_enabled = (
        os.getenv("SESSION_SWEEPER_ENABLED", "1") not in ("0", "false", "off")
    )
    if sweeper_enabled:
        try:
            from agentic.memory.pg_vector.client import get_pool

            pg_pool = await get_pool()
            if pg_pool is not None:
                activity_repo = PostgresSessionActivityRepository(pg_pool=pg_pool)
                finalizer = build_session_finalizer()
                sweeper = SessionSweeper(
                    repo=activity_repo,
                    finalizer=finalizer,
                    config=SweeperConfig(
                        idle_minutes=int(os.getenv("SWEEPER_IDLE_MINUTES", "30")),
                        poll_interval_seconds=float(
                            os.getenv("SWEEPER_POLL_INTERVAL_SECONDS", "60")
                        ),
                        batch_limit=int(os.getenv("SWEEPER_BATCH_LIMIT", "25")),
                        checkpoint_message_threshold=int(
                            os.getenv("SWEEPER_CHECKPOINT_MESSAGE_THRESHOLD", "16")
                        ),
                        recovery_enabled=(
                            os.getenv("SWEEPER_RECOVERY_ENABLED", "1")
                            not in ("0", "false", "off")
                        ),
                        recovery_interval_hours=float(
                            os.getenv("SWEEPER_RECOVERY_INTERVAL_HOURS", "12")
                        ),
                        recovery_cooldown_hours=float(
                            os.getenv("SWEEPER_RECOVERY_COOLDOWN_HOURS", "12")
                        ),
                    ),
                )
                sweeper.start()
                sweeper_task = sweeper._task
                logger.info(
                    "session sweeper started "
                    "(idle=%s min, poll=%s s, batch=%s, checkpoint=%s messages, "
                    "recovery=%s/%sh)",
                    os.getenv("SWEEPER_IDLE_MINUTES", "30"),
                    os.getenv("SWEEPER_POLL_INTERVAL_SECONDS", "60"),
                    os.getenv("SWEEPER_BATCH_LIMIT", "25"),
                    os.getenv("SWEEPER_CHECKPOINT_MESSAGE_THRESHOLD", "16"),
                    os.getenv("SWEEPER_RECOVERY_ENABLED", "1"),
                    os.getenv("SWEEPER_RECOVERY_INTERVAL_HOURS", "12"),
                )
            else:
                logger.warning(
                    "session sweeper disabled: Postgres pool unavailable"
                )
        except Exception as exc:
            logger.error("session sweeper failed to start: %s", exc)
    else:
        logger.info("session sweeper disabled (SESSION_SWEEPER_ENABLED=0)")

    yield

    if decay_task is not None and not decay_task.done():
        decay_task.cancel()
        try:
            await decay_task
        except asyncio.CancelledError:
            pass

    if pgvector_sync_task is not None and not pgvector_sync_task.done():
        pgvector_sync_task.cancel()
        try:
            await pgvector_sync_task
        except asyncio.CancelledError:
            pass

    if sweeper is not None:
        await sweeper.stop()

    logger.info("agentic gateway shut down")


def create_app() -> FastAPI:
    """buat config FastAPI"""
    app = FastAPI(
        title="Companionship Agentic Gateway",
        version="2.0.0",
        description=(
            "Private FastAPI gateway for Companionship LangGraph turns. "
            "Consumed by the Go backend service."
        ),
        lifespan=lifespan,
        docs_url="/docs" if os.getenv("AGENTIC_ENABLE_DOCS") else None,
        redoc_url="/redoc" if os.getenv("AGENTIC_ENABLE_DOCS") else None,
    )

    raw_origins = os.getenv(
        "AGENTIC_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
    )
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(
        PrivateKeyMiddleware,
        private_key=os.getenv("AGENTIC_GATEWAY_PRIVATE_KEY"),
        header_name=os.getenv(
            "AGENTIC_GATEWAY_PRIVATE_KEY_HEADER", "X-Agentic-Private-Key"
        ),
        public_paths=("/health", "/chat/health"),
    )

    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(RuntimeError, runtime_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    register_chat_routes(app)
    register_memory_routes(app)

    @app.get("/health", include_in_schema=False)
    async def root_health() -> dict[str, str]:
        """skip"""
        return {"status": "ok"}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> dict[str, dict[str, int]]:
        """snap priv metrics, agentic key needed."""
        return metrics_snapshot()

    return app


app = create_app()

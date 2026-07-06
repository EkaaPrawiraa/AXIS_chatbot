"""Layer 0 telemetry."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol


logger = logging.getLogger(__name__)



class GuardrailEventLayer(str, Enum):
    INPUT = "input"
    PRE_GEN = "pre_gen"
    POST_GEN = "post_gen"
    KG_ACCESS = "kg_access"


class GuardrailEventDecision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"
    REWRITE = "rewrite"
    FALLBACK = "fallback"
    REDACT = "redact"
    LOG_ONLY = "log_only"


class GuardrailEventSeverity(str, Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"



@dataclass(frozen=True)
class GuardrailEvent:
    """One guardrail observation."""

    user_id: str | None
    session_id: str | None
    layer: GuardrailEventLayer
    event_type: str
    decision: GuardrailEventDecision
    severity: GuardrailEventSeverity = GuardrailEventSeverity.INFO
    trigger_detail: str | None = None
    latency_ms: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_log_line(self) -> str:
        """Compact log representation for stdout fallback."""
        return (
            f"guardrail layer={self.layer.value} type={self.event_type} "
            f"decision={self.decision.value} severity={self.severity.value} "
            f"user={self.user_id} session={self.session_id} "
            f"detail={self.trigger_detail or '-'} "
            f"latency_ms={self.latency_ms or 0}"
        )


# Logger protocol + implementations


class GuardrailLogger(Protocol):
    """Minimal interface so nodes can be unit-tested with fakes."""

    async def log(self, event: GuardrailEvent) -> None: ...


class NullGuardrailLogger:
    """No-op logger. Default in tests and when Postgres is unavailable."""

    def __init__(self) -> None:
        self.events: list[GuardrailEvent] = []

    async def log(self, event: GuardrailEvent) -> None:
        self.events.append(event)
        logger.debug(event.to_log_line())


class PostgresGuardrailLogger:
    """
    Writes events to ``guardrail_events`` via an asyncpg pool.

    Each ``log()`` call schedules a background task and returns
    immediately. The chat turn never waits for the database.

    Task references are kept in ``_pending_tasks`` until the task
    completes. This prevents the CPython garbage collector from
    cancelling in-flight DB inserts when the Task object has no other
    live referent (see module docstring for details).
    """

    def __init__(self, pg_pool: Any) -> None:
        self._pool = pg_pool
        # Strong references to in-flight tasks. Each task removes itself
        # via a done callback so the set does not grow unboundedly.
        self._pending_tasks: set[asyncio.Task[None]] = set()

    async def log(self, event: GuardrailEvent) -> None:
        # log() is always called from an async context, so there is
        # always a running event loop. The previous RuntimeError branch
        # was dead code and has been removed.
        task: asyncio.Task[None] = asyncio.create_task(self._insert(event))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def _insert(self, event: GuardrailEvent) -> None:
        """
        Insert one event row. On FK violation (session not yet committed),
        retry with session_id = NULL so the event is never silently lost.
        """
        try:
            await self._insert_row(event.session_id, event)
        except Exception as exc:
            exc_str = str(exc)
            # Detect FK violation: asyncpg raises asyncpg.ForeignKeyViolationError
            # but we cannot import asyncpg at module level (optional dep).
            # Checking the error class name and message is robust enough.
            is_fk_error = (
                "ForeignKeyViolation" in type(exc).__name__
                or "foreign key constraint" in exc_str.lower()
            )
            if is_fk_error and event.session_id is not None:
                logger.warning(
                    "guardrail event: session_id=%s not in chat_sessions; "
                    "re-inserting with session_id=NULL to preserve audit record. "
                    "Ensure the session row is committed before pipeline invocation.",
                    event.session_id,
                )
                try:
                    await self._insert_row(None, event)
                    return
                except Exception as retry_exc:
                    logger.warning(
                        "guardrail event retry insert failed: %s | %s",
                        retry_exc,
                        event.to_log_line(),
                    )
                    return
            logger.warning(
                "guardrail event insert failed: %s | %s",
                exc,
                event.to_log_line(),
            )

    async def _insert_row(
        self, session_id: str | None, event: GuardrailEvent
    ) -> None:
        """Execute the actual INSERT with the given session_id."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guardrail_events (
                    user_id, session_id, layer, event_type, decision,
                    severity, trigger_detail, latency_ms, metadata,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10
                )
                """,
                event.user_id,
                session_id,
                event.layer.value,
                event.event_type,
                event.decision.value,
                event.severity.value,
                event.trigger_detail,
                event.latency_ms,
                json.dumps(dict(event.metadata or {})),
                event.created_at,
            )

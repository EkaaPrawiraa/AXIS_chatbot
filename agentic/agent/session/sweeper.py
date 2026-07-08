"""bg task finalize expired sessions"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.session.activity_repo import (
    SessionActivity,
    SessionActivityRepository,
)
from agentic.agent.session.finalizer import SessionFinalizer
from agentic.gateway.monitoring import increment


logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class SweeperConfig:
    idle_minutes: int = 30
    poll_interval_seconds: float = 60.0
    batch_limit: int = 25
    max_attempts: int = 3
    checkpoint_message_threshold: int = 16
    recovery_enabled: bool = True
    recovery_interval_hours: float = 12.0
    recovery_cooldown_hours: float = 12.0



@dataclass
class SessionSweeper:
    repo: SessionActivityRepository
    finalizer: SessionFinalizer
    config: SweeperConfig = field(default_factory=SweeperConfig)
    audit: GuardrailLogger = field(default_factory=NullGuardrailLogger)
    _task: asyncio.Task[Any] | None = None
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _last_recovery_at: datetime | None = None
    _last_decay_at: datetime | None = None

    def start(self) -> None:
        """bg poll loop di mulai"""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._loop(), name="session_sweeper")

    async def stop(self) -> None:
        """wait for loop to exit"""
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await self._task
        finally:
            self._task = None

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._recover_retryable_failures_if_due()
                await self._run_memory_decay_if_due()
                await self.run_once()
            except Exception as exc:
                logger.exception("sweeper iteration failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    async def _run_memory_decay_if_due(self) -> None:
        now = datetime.now(timezone.utc)
        if self._last_decay_at is not None:
            if now - self._last_decay_at < timedelta(hours=24):
                return
        self._last_decay_at = now
        try:
            # lazy import: kg_algorithm -> kg_writer
            from agentic.memory.knowledge_graph.kg_algorithm.decay import (
                run_memory_decay,
            )

            stats = await run_memory_decay()
            logger.info("memory decay ran: %s", stats)
        except Exception as exc:
            logger.warning("memory decay failed: %s", exc)

    async def _recover_retryable_failures_if_due(self) -> int:
        if not self.config.recovery_enabled:
            return 0
        now = datetime.now(timezone.utc)
        if self._last_recovery_at is not None:
            interval = timedelta(hours=self.config.recovery_interval_hours)
            if now - self._last_recovery_at < interval:
                return 0

        self._last_recovery_at = now
        recovered = await self.repo.recover_retryable_failures(
            max_attempts=self.config.max_attempts,
            cooldown=timedelta(hours=self.config.recovery_cooldown_hours),
        )
        if recovered:
            logger.info(
                "session finalizer recovery reset %d retryable failure(s)",
                recovered,
            )
            await self.audit.log(
                GuardrailEvent(
                    user_id=None,
                    session_id=None,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_finalize_recovery",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.INFO,
                    metadata={
                        "recovered": recovered,
                        "max_attempts": self.config.max_attempts,
                        "cooldown_hours": self.config.recovery_cooldown_hours,
                    },
                )
            )
        return recovered

    async def run_once(self) -> list[SessionActivity]:
        """handle sessions, return list."""
        handled: list[SessionActivity] = []
        checkpoint_ready = await self.repo.find_checkpoint_ready(
            message_threshold=self.config.checkpoint_message_threshold,
            limit=self.config.batch_limit,
        )
        for row in checkpoint_ready:
            if row.finalize_attempts >= self.config.max_attempts:
                logger.warning(
                    "session %s exceeded max attempts (%d); skipping",
                    row.session_id, row.finalize_attempts,
                )
                continue
            await self._finalize_checkpoint(row)
            handled.append(row)

        idle = timedelta(minutes=self.config.idle_minutes)
        pending = await self.repo.find_pending(
            idle_threshold=idle, limit=self.config.batch_limit,
        )
        for row in pending:
            if row.finalize_attempts >= self.config.max_attempts:
                logger.warning(
                    "session %s exceeded max attempts (%d); skipping",
                    row.session_id, row.finalize_attempts,
                )
                continue
            await self._finalize(row)
            handled.append(row)
        return handled

    async def _finalize_checkpoint(self, row: SessionActivity) -> None:
        through_turn_index = row.latest_turn_index
        result = await self.finalizer.finalize(
            session_id=row.session_id,
            user_id=row.user_id,
            after_turn_index=row.last_finalized_turn_index,
            through_turn_index=through_turn_index,
        )
        if result.ok:
            await self.repo.mark_checkpoint_finalized(
                row.session_id, through_turn_index=through_turn_index,
            )
            await self.audit.log(
                GuardrailEvent(
                    user_id=row.user_id,
                    session_id=row.session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_checkpoint_finalized",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.INFO,
                    metadata={
                        "extracted": result.extracted_count,
                        "processed": result.processed_count,
                        "through_turn_index": through_turn_index,
                    },
                )
            )
        else:
            await self.repo.mark_checkpoint_finalized(
                row.session_id,
                through_turn_index=through_turn_index,
                error=result.error,
            )
            increment("session_finalizer_failures_total", mode="checkpoint")
            await self.audit.log(
                GuardrailEvent(
                    user_id=row.user_id,
                    session_id=row.session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_checkpoint_error",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=(result.error or "")[:200],
                )
            )

    async def _finalize(self, row: SessionActivity) -> None:
        result = await self.finalizer.finalize(
            session_id=row.session_id,
            user_id=row.user_id,
            after_turn_index=row.last_finalized_turn_index,
            through_turn_index=row.latest_turn_index,
        )
        if result.ok:
            await self.repo.mark_finalized(row.session_id)
            await self.audit.log(
                GuardrailEvent(
                    user_id=row.user_id,
                    session_id=row.session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_finalized",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.INFO,
                    metadata={
                        "extracted": result.extracted_count,
                        "processed": result.processed_count,
                        "through_turn_index": row.latest_turn_index,
                    },
                )
            )
        else:
            await self.repo.mark_finalized(row.session_id, error=result.error)
            increment("session_finalizer_failures_total", mode="idle")
            await self.audit.log(
                GuardrailEvent(
                    user_id=row.user_id,
                    session_id=row.session_id,
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_finalize_error",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=(result.error or "")[:200],
                )
            )


__all__ = ["SessionSweeper", "SweeperConfig"]

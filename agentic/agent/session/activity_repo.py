"""stl ses."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol



@dataclass
class SessionActivity:
    session_id: str
    user_id: str
    last_activity_at: datetime
    ai_was_last_speaker: bool = False
    finalized_at: datetime | None = None
    finalize_attempts: int = 0
    last_error: str | None = None
    latest_turn_index: int = 0
    last_finalized_turn_index: int = -1
    last_checkpoint_at: datetime | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))



class SessionActivityRepository(Protocol):
    async def upsert_activity(
        self,
        *,
        session_id: str,
        user_id: str,
        ai_was_last_speaker: bool,
        at: datetime | None = None,
        latest_turn_index: int | None = None,
    ) -> SessionActivity: ...

    async def find_pending(
        self,
        *,
        idle_threshold: timedelta,
        limit: int,
        now: datetime | None = None,
    ) -> list[SessionActivity]: ...

    async def mark_finalized(
        self, session_id: str, *, error: str | None = None,
    ) -> None: ...

    async def find_checkpoint_ready(
        self,
        *,
        message_threshold: int,
        limit: int,
    ) -> list[SessionActivity]: ...

    async def mark_checkpoint_finalized(
        self,
        session_id: str,
        *,
        through_turn_index: int,
        error: str | None = None,
    ) -> None: ...

    async def recover_retryable_failures(
        self,
        *,
        max_attempts: int,
        cooldown: timedelta,
    ) -> int: ...


# inmem impl (tests, dev)


class InMemorySessionActivityRepository:
    def __init__(self) -> None:
        self._rows: dict[str, SessionActivity] = {}
        self._lock = asyncio.Lock()

    async def upsert_activity(
        self,
        *,
        session_id: str,
        user_id: str,
        ai_was_last_speaker: bool,
        at: datetime | None = None,
        latest_turn_index: int | None = None,
    ) -> SessionActivity:
        ts = at or datetime.now(timezone.utc)
        turn = max(0, int(latest_turn_index or 0))
        async with self._lock:
            existing = self._rows.get(session_id)
            if existing is None:
                row = SessionActivity(
                    session_id=session_id,
                    user_id=user_id,
                    last_activity_at=ts,
                    ai_was_last_speaker=ai_was_last_speaker,
                    latest_turn_index=turn,
                    updated_at=ts,
                )
                self._rows[session_id] = row
            else:
                existing.last_activity_at = ts
                existing.ai_was_last_speaker = ai_was_last_speaker
                existing.latest_turn_index = max(existing.latest_turn_index, turn)
                existing.updated_at = ts
                # reset
                if existing.finalized_at is not None:
                    existing.finalized_at = None
                    existing.finalize_attempts = 0
                    existing.last_error = None
                row = existing
        return row

    async def find_pending(
        self,
        *,
        idle_threshold: timedelta,
        limit: int,
        now: datetime | None = None,
    ) -> list[SessionActivity]:
        cutoff = (now or datetime.now(timezone.utc)) - idle_threshold
        out: list[SessionActivity] = []
        async with self._lock:
            for row in self._rows.values():
                if row.finalized_at is not None:
                    continue
                if not row.ai_was_last_speaker:
                    continue
                if row.last_activity_at <= cutoff:
                    out.append(row)
                if len(out) >= limit:
                    break
        return out

    async def mark_finalized(
        self, session_id: str, *, error: str | None = None,
    ) -> None:
        async with self._lock:
            row = self._rows.get(session_id)
            if row is None:
                return
            if error:
                row.finalize_attempts += 1
                row.last_error = error
                row.updated_at = datetime.now(timezone.utc)
                # skip fin.
                return
            row.finalized_at = datetime.now(timezone.utc)
            row.last_finalized_turn_index = max(
                row.last_finalized_turn_index, row.latest_turn_index
            )
            row.last_checkpoint_at = row.finalized_at
            row.last_error = None
            row.updated_at = row.finalized_at

    async def find_checkpoint_ready(
        self,
        *,
        message_threshold: int,
        limit: int,
    ) -> list[SessionActivity]:
        threshold = max(1, message_threshold)
        out: list[SessionActivity] = []
        async with self._lock:
            for row in self._rows.values():
                if row.finalized_at is not None or not row.ai_was_last_speaker:
                    continue
                gap = row.latest_turn_index - row.last_finalized_turn_index
                if gap >= threshold:
                    out.append(row)
                if len(out) >= limit:
                    break
        return out

    async def mark_checkpoint_finalized(
        self,
        session_id: str,
        *,
        through_turn_index: int,
        error: str | None = None,
    ) -> None:
        async with self._lock:
            row = self._rows.get(session_id)
            if row is None:
                return
            if error:
                row.finalize_attempts += 1
                row.last_error = error
                row.updated_at = datetime.now(timezone.utc)
                return
            now = datetime.now(timezone.utc)
            row.last_finalized_turn_index = max(
                row.last_finalized_turn_index, through_turn_index
            )
            row.last_checkpoint_at = now
            row.last_error = None
            row.updated_at = now

    async def recover_retryable_failures(
        self,
        *,
        max_attempts: int,
        cooldown: timedelta,
    ) -> int:
        now = datetime.now(timezone.utc)
        cutoff = now - cooldown
        recovered = 0
        async with self._lock:
            for row in self._rows.values():
                if row.finalized_at is not None:
                    continue
                if row.finalize_attempts < max_attempts:
                    continue
                if not row.last_error or not _is_retryable_error(row.last_error):
                    continue
                if row.updated_at > cutoff:
                    continue
                row.finalize_attempts = 0
                row.last_error = None
                row.updated_at = now
                recovered += 1
        return recovered



class PostgresSessionActivityRepository:
    """buat nyimpan config"""

    def __init__(self, *, pg_pool: Any) -> None:
        self._pool = pg_pool

    async def upsert_activity(
        self,
        *,
        session_id: str,
        user_id: str,
        ai_was_last_speaker: bool,
        at: datetime | None = None,
        latest_turn_index: int | None = None,
    ) -> SessionActivity:
        ts = at or datetime.now(timezone.utc)
        turn = max(0, int(latest_turn_index or 0))
        sql = (
            "INSERT INTO session_activity "
            "(session_id, user_id, last_activity_at, ai_was_last_speaker, latest_turn_index) "
            "VALUES ($1, $2, $3, $4, $5) "
            "ON CONFLICT (session_id) DO UPDATE SET "
            "  last_activity_at = EXCLUDED.last_activity_at, "
            "  ai_was_last_speaker = EXCLUDED.ai_was_last_speaker, "
            "  latest_turn_index = GREATEST(session_activity.latest_turn_index, EXCLUDED.latest_turn_index), "
            "  finalized_at = CASE "
            "     WHEN EXCLUDED.last_activity_at > session_activity.finalized_at "
            "          THEN NULL "
            "     ELSE session_activity.finalized_at "
            "  END, "
            "  updated_at = NOW() "
            "RETURNING last_activity_at, finalize_attempts, last_error, finalized_at, "
            "          latest_turn_index, last_finalized_turn_index, last_checkpoint_at, updated_at"
        )
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                sql, session_id, user_id, ts, ai_was_last_speaker, turn
            )
        return SessionActivity(
            session_id=session_id,
            user_id=user_id,
            last_activity_at=row["last_activity_at"],
            ai_was_last_speaker=ai_was_last_speaker,
            finalized_at=row["finalized_at"],
            finalize_attempts=row["finalize_attempts"],
            last_error=row["last_error"],
            latest_turn_index=row["latest_turn_index"],
            last_finalized_turn_index=row["last_finalized_turn_index"],
            last_checkpoint_at=row["last_checkpoint_at"],
            updated_at=row["updated_at"],
        )

    async def find_pending(
        self,
        *,
        idle_threshold: timedelta,
        limit: int,
        now: datetime | None = None,
    ) -> list[SessionActivity]:
        ref = now or datetime.now(timezone.utc)
        cutoff = ref - idle_threshold
        sql = (
            "SELECT session_id, user_id, last_activity_at, "
            "       ai_was_last_speaker, finalized_at, "
            "       finalize_attempts, last_error, "
            "       latest_turn_index, last_finalized_turn_index, last_checkpoint_at, updated_at "
            "FROM session_activity "
            "WHERE finalized_at IS NULL "
            "  AND ai_was_last_speaker = TRUE "
            "  AND last_activity_at <= $1 "
            "ORDER BY last_activity_at ASC "
            "LIMIT $2"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, cutoff, limit)
        return [
            SessionActivity(
                session_id=str(r["session_id"]),
                user_id=str(r["user_id"]),
                last_activity_at=r["last_activity_at"],
                ai_was_last_speaker=r["ai_was_last_speaker"],
                finalized_at=r["finalized_at"],
                finalize_attempts=r["finalize_attempts"],
                last_error=r["last_error"],
                latest_turn_index=r["latest_turn_index"],
                last_finalized_turn_index=r["last_finalized_turn_index"],
                last_checkpoint_at=r["last_checkpoint_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def mark_finalized(
        self, session_id: str, *, error: str | None = None,
    ) -> None:
        if error:
            sql = (
                "UPDATE session_activity SET "
                "  finalize_attempts = finalize_attempts + 1, "
                "  last_error = $2, "
                "  updated_at = NOW() "
                "WHERE session_id = $1"
            )
            params: tuple = (session_id, error[:1000])
        else:
            sql = (
                "UPDATE session_activity SET "
                "  finalized_at = NOW(), "
                "  last_finalized_turn_index = GREATEST(last_finalized_turn_index, latest_turn_index), "
                "  last_checkpoint_at = NOW(), "
                "  last_error = NULL, "
                "  updated_at = NOW() "
                "WHERE session_id = $1"
            )
            params = (session_id,)
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def find_checkpoint_ready(
        self,
        *,
        message_threshold: int,
        limit: int,
    ) -> list[SessionActivity]:
        threshold = max(1, message_threshold)
        sql = (
            "SELECT session_id, user_id, last_activity_at, "
            "       ai_was_last_speaker, finalized_at, "
            "       finalize_attempts, last_error, "
            "       latest_turn_index, last_finalized_turn_index, last_checkpoint_at, updated_at "
            "FROM session_activity "
            "WHERE finalized_at IS NULL "
            "  AND ai_was_last_speaker = TRUE "
            "  AND latest_turn_index - last_finalized_turn_index >= $1 "
            "ORDER BY last_activity_at ASC "
            "LIMIT $2"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, threshold, limit)
        return [
            SessionActivity(
                session_id=str(r["session_id"]),
                user_id=str(r["user_id"]),
                last_activity_at=r["last_activity_at"],
                ai_was_last_speaker=r["ai_was_last_speaker"],
                finalized_at=r["finalized_at"],
                finalize_attempts=r["finalize_attempts"],
                last_error=r["last_error"],
                latest_turn_index=r["latest_turn_index"],
                last_finalized_turn_index=r["last_finalized_turn_index"],
                last_checkpoint_at=r["last_checkpoint_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def mark_checkpoint_finalized(
        self,
        session_id: str,
        *,
        through_turn_index: int,
        error: str | None = None,
    ) -> None:
        if error:
            sql = (
                "UPDATE session_activity SET "
                "  finalize_attempts = finalize_attempts + 1, "
                "  last_error = $2, "
                "  updated_at = NOW() "
                "WHERE session_id = $1"
            )
            params: tuple = (session_id, error[:1000])
        else:
            sql = (
                "UPDATE session_activity SET "
                "  last_finalized_turn_index = GREATEST(last_finalized_turn_index, $2), "
                "  last_checkpoint_at = NOW(), "
                "  last_error = NULL, "
                "  updated_at = NOW() "
                "WHERE session_id = $1"
            )
            params = (session_id, through_turn_index)
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def recover_retryable_failures(
        self,
        *,
        max_attempts: int,
        cooldown: timedelta,
    ) -> int:
        sql = (
            "UPDATE session_activity sa "
            "SET finalize_attempts = 0, "
            "    last_error = NULL, "
            "    updated_at = NOW() "
            "WHERE sa.finalized_at IS NULL "
            "  AND sa.finalize_attempts >= $1 "
            "  AND sa.last_error IS NOT NULL "
            "  AND sa.updated_at <= NOW() - $2::interval "
            "  AND EXISTS ( "
            "      SELECT 1 "
            "      FROM messages m "
            "      WHERE m.session_id = sa.session_id "
            "  ) "
            "  AND ( "
            "      sa.last_error ILIKE '%timeout%' "
            "      OR sa.last_error ILIKE '%rate%' "
            "      OR sa.last_error ILIKE '%quota%' "
            "      OR sa.last_error ILIKE '%connection%' "
            "      OR sa.last_error ILIKE '%temporarily%' "
            "      OR sa.last_error ILIKE '%llm%' "
            "  ) "
            "RETURNING sa.session_id"
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, max_attempts, cooldown)
        return len(rows)


def _is_retryable_error(error: str) -> bool:
    lowered = error.lower()
    return any(
        token in lowered
        for token in ("timeout", "rate", "quota", "connection", "temporarily", "llm")
    )


__all__ = [
    "SessionActivity",
    "SessionActivityRepository",
    "InMemorySessionActivityRepository",
    "PostgresSessionActivityRepository",
]

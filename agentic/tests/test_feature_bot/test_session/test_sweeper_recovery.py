"""test sess fin recovery"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from agentic.agent.session.activity_repo import InMemorySessionActivityRepository
from agentic.agent.session.finalizer import FinalizationResult
from agentic.agent.session.sweeper import SessionSweeper, SweeperConfig


class _NoopFinalizer:
    async def finalize(self, **kwargs) -> FinalizationResult:
        return FinalizationResult(
            session_id=kwargs["session_id"],
            summary="",
            extracted_count=0,
        )


@pytest.mark.asyncio
async def test_recovery_resets_old_retryable_failure() -> None:
    repo = InMemorySessionActivityRepository()
    old = datetime.now(timezone.utc) - timedelta(hours=13)
    await repo.upsert_activity(
        session_id="s1",
        user_id="u1",
        ai_was_last_speaker=True,
        at=old,
        latest_turn_index=3,
    )
    row = repo._rows["s1"]
    row.finalize_attempts = 3
    row.last_error = "llm timeout while writing kg"
    row.updated_at = old

    sweeper = SessionSweeper(
        repo=repo,
        finalizer=_NoopFinalizer(),
        config=SweeperConfig(
            max_attempts=3,
            recovery_interval_hours=12,
            recovery_cooldown_hours=12,
        ),
    )

    recovered = await sweeper._recover_retryable_failures_if_due()

    assert recovered == 1
    assert row.finalize_attempts == 0
    assert row.last_error is None


@pytest.mark.asyncio
async def test_recovery_keeps_recent_or_permanent_failure() -> None:
    repo = InMemorySessionActivityRepository()
    old = datetime.now(timezone.utc) - timedelta(hours=13)
    recent = datetime.now(timezone.utc) - timedelta(hours=2)
    await repo.upsert_activity(
        session_id="recent",
        user_id="u1",
        ai_was_last_speaker=True,
        at=recent,
        latest_turn_index=3,
    )
    await repo.upsert_activity(
        session_id="permanent",
        user_id="u1",
        ai_was_last_speaker=True,
        at=old,
        latest_turn_index=3,
    )
    repo._rows["recent"].finalize_attempts = 3
    repo._rows["recent"].last_error = "connection timeout"
    repo._rows["recent"].updated_at = recent
    repo._rows["permanent"].finalize_attempts = 3
    repo._rows["permanent"].last_error = "schema violation"
    repo._rows["permanent"].updated_at = old

    sweeper = SessionSweeper(
        repo=repo,
        finalizer=_NoopFinalizer(),
        config=SweeperConfig(
            max_attempts=3,
            recovery_interval_hours=12,
            recovery_cooldown_hours=12,
        ),
    )

    recovered = await sweeper._recover_retryable_failures_if_due()

    assert recovered == 0
    assert repo._rows["recent"].finalize_attempts == 3
    assert repo._rows["permanent"].finalize_attempts == 3

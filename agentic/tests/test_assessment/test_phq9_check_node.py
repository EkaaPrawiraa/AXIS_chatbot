"""test node PHQ-9"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.state import empty_conversation_state, empty_phq9_state
from agentic.assessment.phq9 import PHQ9Severity
from agentic.memory.assessment_repo import (
    DistressSnapshot,
    LastPHQ9Snapshot,
)



def _state(
    *,
    user_id: str = "u1",
    session_id: str = "s1",
    last_user_message: str = "",
    history: list[dict[str, Any]] | None = None,
    session_turn: int = 0,
    language_pref: str | None = None,
):
    state = empty_conversation_state(
        user_id=user_id,
        session_id=session_id,
        language_pref=language_pref,
    )
    state["session_turn"] = session_turn
    state["current_message"] = last_user_message
    state["messages"] = history or []
    return state



class TestTier1:
    @pytest.mark.asyncio
    async def test_first_time_user_offer_pending(self, fake_repo) -> None:
        state = _state(
            last_user_message="halo, lagi capek nih",
            language_pref="id",
        )
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "offer_pending"
        assert phq9["tier"] == "scheduled"
        assert phq9["reason"] == "scheduled_14d"
        assert out["resolved_language"] == "id"

    @pytest.mark.asyncio
    async def test_recent_phq9_does_not_trigger(self, fake_repo) -> None:
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=3),
            total_score=8,
            severity=PHQ9Severity.MILD,
            item_scores=(1,) * 9,
        )
        state = _state(last_user_message="halo")
        out = await phq9_check_node(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "idle"

    @pytest.mark.asyncio
    async def test_acute_distress_suppresses_and_schedules_retry(
        self, fake_repo
    ) -> None:
        # skip error
        fake_repo.state.distress = DistressSnapshot(
            high_distress_session_count_7d=0,
            avg_emotion_valence_7d=-0.8,
            recurring_trigger_active=False,
        )
        state = _state(last_user_message="aku ga sanggup lagi")
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "idle"
        assert phq9["reason"] == "suppressed:acute_distress"
        assert phq9["retry_scheduled_at"] is not None
        assert fake_repo.state.scheduled_retries
        user_id, days, reason = fake_repo.state.scheduled_retries[-1]
        assert reason == "acute_distress"
        assert days == 3

    @pytest.mark.asyncio
    async def test_recently_severe_without_delta_allows_scheduled_check(
        self, fake_repo
    ) -> None:
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=20),
            total_score=22,
            severity=PHQ9Severity.SEVERE,
            item_scores=(2,) * 9,
        )
        state = _state(last_user_message="halo")
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "offer_pending"
        assert phq9["reason"] == "scheduled_14d"
        assert fake_repo.state.scheduled_retries == []

    @pytest.mark.asyncio
    async def test_recent_worsening_delta_triggers_seven_day_cool_down(
        self, fake_repo
    ) -> None:
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=20),
            total_score=22,
            severity=PHQ9Severity.SEVERE,
            item_scores=(2,) * 9,
            delta_from_prev=4,
        )
        state = _state(last_user_message="halo")
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["reason"] == "suppressed:recent_worsening"
        user_id, days, reason = fake_repo.state.scheduled_retries[-1]
        assert reason == "recent_worsening"
        assert days == 7

    @pytest.mark.asyncio
    async def test_active_retry_blocks_offer(self, fake_repo) -> None:
        from agentic.memory.assessment_repo import AssessmentRetrySchedule

        fake_repo.state.pending_retry = AssessmentRetrySchedule(
            user_id="u1",
            next_attempt_at=datetime.now(timezone.utc) + timedelta(days=2),
            reason="acute_distress",
        )
        state = _state(last_user_message="halo")
        out = await phq9_check_node(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "idle"



class TestTier2:
    @pytest.mark.asyncio
    async def test_event_cluster_with_high_distress_count(
        self, fake_repo
    ) -> None:
        # limit admin 1 14 hari
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=5),
            total_score=8,
            severity=PHQ9Severity.MILD,
            item_scores=(1,) * 9,
        )
        fake_repo.state.distress = DistressSnapshot(
            high_distress_session_count_7d=3,
            avg_emotion_valence_7d=-0.3,
            recurring_trigger_active=False,
        )
        state = _state(last_user_message="capek banget")
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "offer_pending"
        assert phq9["tier"] == "event"
        assert "high_distress_sessions" in (phq9["reason"] or "")

    @pytest.mark.asyncio
    async def test_event_recurring_trigger_active(self, fake_repo) -> None:
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=5),
            total_score=4,
            severity=PHQ9Severity.MINIMAL,
            item_scores=(0,) * 9,
        )
        fake_repo.state.distress = DistressSnapshot(
            high_distress_session_count_7d=0,
            avg_emotion_valence_7d=-0.2,
            recurring_trigger_active=True,
        )
        state = _state(last_user_message="ketemu mantan lagi")
        out = await phq9_check_node(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "offer_pending"
        assert phq9["tier"] == "event"

    # remov 2026-05, helper, per-turn, emo' pad.

    @pytest.mark.asyncio
    async def test_event_acute_distress_suppresses(self, fake_repo) -> None:
        fake_repo.state.last = LastPHQ9Snapshot(
            administered_at=datetime.now(timezone.utc) - timedelta(days=5),
            total_score=4,
            severity=PHQ9Severity.MINIMAL,
            item_scores=(0,) * 9,
        )
        # pad, kg, rely.
        fake_repo.state.distress = DistressSnapshot(
            high_distress_session_count_7d=3,
            avg_emotion_valence_7d=-0.8,
            recurring_trigger_active=False,
        )
        state = _state(last_user_message="aku ga sanggup")
        out = await phq9_check_node(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "idle"
        assert out["phq9_state"]["reason"] == "suppressed:event_acute_distress"



class TestIdempotence:
    @pytest.mark.asyncio
    async def test_node_short_circuits_when_already_engaged(
        self, fake_repo
    ) -> None:
        state = _state(last_user_message="halo")
        # qanda
        state["phq9_state"] = empty_phq9_state()
        state["phq9_state"]["phase"] = "in_progress"
        state["phq9_state"]["active_item"] = 4
        out = await phq9_check_node(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "in_progress"
        assert out["phq9_state"]["active_item"] == 4

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.state import empty_conversation_state
from agentic.memory.assessment_repo import DistressSnapshot


@dataclass
class FakeAssessmentRepo:
    last_phq9: Any = None
    progress: dict[str, Any] | None = None

    async def load_phq9_progress(
        self, *, user_id: str, session_id: str,
    ) -> dict[str, Any] | None:
        return self.progress

    async def save_phq9_progress(
        self, *, user_id: str, session_id: str, state: dict[str, Any],
    ) -> None:
        self.progress = dict(state)

    async def get_pending_retry(self, user_id: str) -> Any:
        return None

    async def get_last_phq9(self, user_id: str) -> Any:
        return self.last_phq9

    async def get_conversation_count(self, user_id: str) -> int:
        return 0

    async def get_distress_snapshot(self, user_id: str) -> DistressSnapshot:
        return DistressSnapshot(
            high_distress_session_count_7d=0,
            avg_emotion_valence_7d=None,
            recurring_trigger_active=False,
        )


def _state(*, turn: int, onboarding_complete: bool):
    state = empty_conversation_state(
        user_id="11111111-1111-1111-1111-111111111111",
        session_id="22222222-2222-2222-2222-222222222222",
        language_pref="id",
    )
    state["session_turn"] = turn
    state["current_message"] = "aku lagi cerita biasa"
    state["profile_context"] = {
        "display_name": "Rafid",
        "preferred_language": "id",
        "onboarding_complete": onboarding_complete,
    }
    return state


@pytest.mark.asyncio
async def test_onboarding_false_turn_10_triggers_phq9_offer_pending() -> None:
    repo = FakeAssessmentRepo()
    state = _state(turn=10, onboarding_complete=False)

    out = await phq9_check_node(state, repo=repo)

    phq9 = out["phq9_state"]
    assert phq9["phase"] == "offer_pending"
    assert phq9["tier"] == "onboarding"
    assert phq9["reason"] == "onboarding_turn_10"
    assert repo.progress is not None


@pytest.mark.asyncio
async def test_onboarding_true_does_not_trigger_phq9_offer() -> None:
    repo = FakeAssessmentRepo()
    state = _state(turn=10, onboarding_complete=True)

    out = await phq9_check_node(state, repo=repo)

    phq9 = out["phq9_state"]
    assert phq9["phase"] == "idle"
    assert repo.progress is None


@pytest.mark.asyncio
async def test_onboarding_false_before_turn_10_does_not_trigger_phq9_offer() -> None:
    repo = FakeAssessmentRepo()
    state = _state(turn=9, onboarding_complete=False)

    out = await phq9_check_node(state, repo=repo)

    phq9 = out["phq9_state"]
    assert phq9["phase"] == "idle"
    assert repo.progress is None

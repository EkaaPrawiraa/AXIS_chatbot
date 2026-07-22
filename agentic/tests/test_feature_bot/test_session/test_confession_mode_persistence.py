"""skip conv discovery"""

from __future__ import annotations

import pytest

from agentic.agent.nodes.session_end import session_end_node


class _RecordingActivityRepo:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def upsert_activity(self, *, session_id, user_id, ai_was_last_speaker, latest_turn_index):
        self.calls.append({
            "session_id": session_id,
            "user_id": user_id,
            "ai_was_last_speaker": ai_was_last_speaker,
            "latest_turn_index": latest_turn_index,
        })


def _base_state(*, confession_mode: bool) -> dict:
    return {
        "user_id": "user-confession-test",
        "session_id": "session-confession-test",
        "current_message": "cerita rahasia yang tidak ingin diingat",
        "final_response": "Terima kasih sudah cerita, aku di sini dengarin.",
        "session_turn": 0,
        "confession_mode": confession_mode,
        "messages": [],
    }


class TestConfessionModeSkipsActivityUpsert:
    @pytest.mark.asyncio
    async def test_confession_mode_true_never_upserts_activity(self) -> None:
        repo = _RecordingActivityRepo()
        state = _base_state(confession_mode=True)

        await session_end_node(state, activity_repo=repo)

        assert repo.calls == []

    @pytest.mark.asyncio
    async def test_confession_mode_false_upserts_activity(self) -> None:
        repo = _RecordingActivityRepo()
        state = _base_state(confession_mode=False)

        await session_end_node(state, activity_repo=repo)

        assert len(repo.calls) == 1
        assert repo.calls[0]["session_id"] == "session-confession-test"
        assert repo.calls[0]["user_id"] == "user-confession-test"

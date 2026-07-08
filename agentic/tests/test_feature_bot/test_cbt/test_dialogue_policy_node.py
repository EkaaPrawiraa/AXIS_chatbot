"""test dialog policy"""

from __future__ import annotations

import pytest

from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.dialogue_policy import dialogue_policy_node
from agentic.agent.state import empty_conversation_state


def _state_with_message(msg: str, *, resolved_language="id"):
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = msg
    state["resolved_language"] = resolved_language
    return state


class TestDecisionWiring:
    @pytest.mark.asyncio
    async def test_default_validate(self, audit) -> None:
        state = _state_with_message("capek banget hari ini abis kelas")
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "validate"
        assert out["cbt_directive"]["technique"] == "validate"
        assert audit.technique_events()

    @pytest.mark.asyncio
    async def test_casual_message_wires_to_none(self, audit) -> None:
        """wire cbt_node_active to "none"""
        state = _state_with_message("halo, hari ini gimana")
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "none"
        assert out["cbt_directive"]["technique"] == "none"

    @pytest.mark.asyncio
    async def test_distortion_offers_reframe(self, audit) -> None:
        state = _state_with_message("aku selalu gagal di mata kuliah ini")
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "reframe"
        assert out["cbt_state"]["last_offered"] == "reframe"

    # rm field 2026-05: emotion_pad field 2026-05: emotion_detection Acute affect 2026-05: LLM judge

    @pytest.mark.asyncio
    async def test_safety_flag_blocks(self, audit) -> None:
        state = _state_with_message("apapun")
        state["safety_flag"] = "crisis"
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "none"

    @pytest.mark.asyncio
    async def test_phq9_active_blocks(self, audit) -> None:
        state = _state_with_message("aku selalu gagal")
        state["phq9_state"] = {"phase": "in_progress"}  # type: ignore[typeddict-item]
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "none"


class TestDeclineCooldown:
    @pytest.mark.asyncio
    async def test_decline_marks_state(self, audit) -> None:
        state = _state_with_message("ga usah deh")
        state["cbt_state"] = {"last_offered": "reframe"}  # type: ignore[typeddict-item]
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_state"]["declined_last_offer"] is True
        assert out["cbt_state"]["decline_streak"] == 1

    @pytest.mark.asyncio
    async def test_after_decline_router_falls_back_to_validate(self, audit) -> None:
        # cool down offer
        state = _state_with_message("aku selalu gagal")
        state["cbt_state"] = {  # type: ignore[typeddict-item]
            "last_offered": "reframe",
            "declined_last_offer": True,
            "decline_streak": 1,
        }
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "validate"
        assert out["cbt_directive"]["reason"] == "opt_out_cooldown"

    @pytest.mark.asyncio
    async def test_decline_turn_flag_stays_true(self, audit) -> None:
        """bug-fix: set flag to True, reset in next node."""
        state = _state_with_message("Nggak deh, ga usah dibahas lagi soal itu.")
        state["cbt_state"] = {  # type: ignore[typeddict-item]
            "last_offered": "reframe",
            "declined_last_offer": False,
            "decline_streak": 0,
        }
        out = await dialogue_policy_node(state, audit=audit, judge_llm=None)
        actual = out["cbt_state"]["declined_last_offer"]
        assert actual is True, (
            f"FAIL: expected declined_last_offer=True on the decline turn, got {actual!r}"
        )

    @pytest.mark.asyncio
    async def test_next_turn_after_decline_resets_flag(self, audit) -> None:
        """reset to False"""
        # declined_last_offer=True, next msg triggers same technique, demote to opt_out_cooldown, node consumes cooldown.
        state = _state_with_message("aku selalu gagal di mata kuliah ini")
        state["cbt_state"] = {  # type: ignore[typeddict-item]
            "last_offered": "reframe",
            "declined_last_offer": True,
            "decline_streak": 1,
        }
        out = await dialogue_policy_node(state, audit=audit, judge_llm=None)
        # opt_out_cooldown
        assert out["cbt_directive"]["reason"] == "opt_out_cooldown", (
            f"FAIL: expected opt_out_cooldown reason, got {out['cbt_directive']['reason']!r}"
        )
        actual = out["cbt_state"]["declined_last_offer"]
        assert actual is False, (
            f"FAIL: expected declined_last_offer=False after cooldown consumed, got {actual!r}"
        )


class TestThoughtRecordDriven:
    @pytest.mark.asyncio
    async def test_explicit_request_starts_thought_record(self, audit) -> None:
        state = _state_with_message(
            "aku pasti gagal final, bantu reframe dong",
        )
        out = await dialogue_policy_node(state, audit=audit)
        assert out["cbt_node_active"] == "thought_record"
        directive = out["cbt_directive"]
        assert "step" in directive["payload"]
        assert "bot_prompt" in directive["payload"]
        assert out["cbt_state"]["thought_record_active"] is True

    @pytest.mark.asyncio
    async def test_resume_advances_step(self, audit) -> None:
        state = _state_with_message(
            "aku pasti gagal final, bantu reframe dong",
        )
        out = await dialogue_policy_node(state, audit=audit)
        first_step = out["cbt_directive"]["payload"]["step"]

        # answering prompt
        out["current_message"] = "aku pasti gagal final besok"
        out2 = await dialogue_policy_node(out, audit=audit)
        second_step = out2["cbt_directive"]["payload"]["step"]
        assert second_step != first_step

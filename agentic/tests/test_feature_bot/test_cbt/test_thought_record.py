"""
Tests for the five-step thought record state machine.
"""

from __future__ import annotations

import pytest

from agentic.agent.cbt.distortions import DISTORTIONS
from agentic.agent.cbt.thought_record import (
    ThoughtRecordMachine,
    ThoughtRecordStep,
    ThoughtRecordSubState,
)


@pytest.mark.asyncio
async def test_full_run_with_hinted_distortion() -> None:
    machine = ThoughtRecordMachine()
    sub = ThoughtRecordSubState()
    hint = DISTORTIONS["catastrophizing"]

    # Step 1: opening
    turn = await machine.step(
        sub_state=sub, user_reply="", language="id",
        hinted_distortion=hint,
    )
    assert turn.next_state.step is ThoughtRecordStep.CATCH_THOUGHT
    assert "satu kalimat" in turn.bot_prompt.lower()

    # Step 2: capture thought, prompt distortion
    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku pasti gagal final besok",
        language="id",
        hinted_distortion=hint,
    )
    assert turn.next_state.step is ThoughtRecordStep.LABEL_DISTORTION
    assert turn.next_state.thought == "aku pasti gagal final besok"
    assert "bencana" in turn.bot_prompt.lower()

    # Step 3: confirm distortion, prompt evidence_for
    turn = await machine.step(
        sub_state=turn.next_state, user_reply="iya",
        language="id", hinted_distortion=hint,
    )
    assert turn.next_state.step is ThoughtRecordStep.EVIDENCE_FOR
    assert turn.next_state.distortion == "catastrophizing"

    # Step 4: evidence_for -> evidence_against
    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku belum belajar materi bab terakhir",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.EVIDENCE_AGAINST
    assert turn.next_state.evidence_for

    # Step 5: evidence_against -> balanced_thought
    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku tetap dapat nilai bagus di kuis sebelumnya",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.BALANCED_THOUGHT

    # Step 6: balanced -> done
    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku belum menguasai semua bab tapi masih bisa lulus dengan persiapan ekstra",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.DONE
    assert turn.completed is True


@pytest.mark.asyncio
async def test_persistence_round_trip() -> None:
    sub = ThoughtRecordSubState(
        step=ThoughtRecordStep.EVIDENCE_FOR,
        thought="aku pasti gagal",
        distortion="catastrophizing",
    )
    serialized = sub.to_dict()
    rehydrated = ThoughtRecordSubState.from_dict(serialized)
    assert rehydrated.step is ThoughtRecordStep.EVIDENCE_FOR
    assert rehydrated.thought == "aku pasti gagal"
    assert rehydrated.distortion == "catastrophizing"


@pytest.mark.asyncio
async def test_english_language() -> None:
    machine = ThoughtRecordMachine()
    sub = ThoughtRecordSubState()
    turn = await machine.step(sub_state=sub, user_reply="", language="en")
    assert "thought" in turn.bot_prompt.lower()

"""regression: LLM self-counting name usage across the system prompt proved
unreliable on real scripted-persona runs (2026-07-12), so the guard is
computed deterministically from conversation history instead."""

from __future__ import annotations

from agentic.agent.nodes.response_generator import (
    _looks_like_human_display_name,
    _question_ending_note,
    _recent_name_usage_note,
)


def _state(*, display_name: str, assistant_turns: list[str]) -> dict:
    messages = []
    for i, content in enumerate(assistant_turns):
        messages.append({"role": "user", "content": f"turn {i}"})
        messages.append({"role": "assistant", "content": content})
    return {
        "profile_context": {"display_name": display_name},
        "messages": messages,
    }


def test_no_note_when_name_never_used() -> None:
    state = _state(
        display_name="Arya",
        assistant_turns=["Gimana kabarmu hari ini?", "Wah seru banget ceritanya."],
    )
    assert _recent_name_usage_note(state) == ""


def test_hard_note_when_name_used_last_turn() -> None:
    state = _state(
        display_name="Arya",
        assistant_turns=["Gimana kabarmu?", "Semangat ya, Arya, kamu pasti bisa."],
    )
    note = _recent_name_usage_note(state)
    assert "immediately preceding turn" in note
    assert "no exceptions" in note.lower()


def test_soft_note_when_name_used_two_turns_ago_but_not_last() -> None:
    state = _state(
        display_name="Arya",
        assistant_turns=["Semangat ya, Arya.", "Gimana rasanya sekarang?"],
    )
    note = _recent_name_usage_note(state)
    assert "recently" in note
    assert "immediately preceding turn" not in note


def test_no_note_when_display_name_missing() -> None:
    state = _state(display_name="", assistant_turns=["Halo, gimana kabarnya?"])
    assert _recent_name_usage_note(state) == ""


def test_no_note_when_display_name_looks_like_seed_account() -> None:
    # _looks_like_human_display_name should reject seed/test-style names
    state = _state(
        display_name="test_user_001",
        assistant_turns=["Halo test_user_001, gimana kabarnya?"],
    )
    assert _recent_name_usage_note(state) == ""


def test_case_insensitive_match() -> None:
    state = _state(
        display_name="Arya",
        assistant_turns=["Gimana kabarmu?", "Semangat ya, ARYA!"],
    )
    note = _recent_name_usage_note(state)
    assert "immediately preceding turn" in note


def test_seed_display_name_with_evaluasi_is_rejected() -> None:
    # Real bug found via a real 2-session/20-turn run (2026-07-13): the
    # evaluation harness's seed display name "Budi Evaluasi" passed the old
    # filter and leaked into 3-5 of 20 real turns, because the banned-parts
    # list had no "eval"/"evaluasi" entry.
    assert not _looks_like_human_display_name("Budi Evaluasi")
    state = _state(
        display_name="Budi Evaluasi",
        assistant_turns=["Halo, gimana kabarnya?"],
    )
    assert _recent_name_usage_note(state) == ""


def test_real_name_still_accepted() -> None:
    assert _looks_like_human_display_name("Nugraha")
    assert _looks_like_human_display_name("Siti Rahma")


def _q_state(assistant_turns: list[str]) -> dict:
    messages = []
    for i, content in enumerate(assistant_turns):
        messages.append({"role": "user", "content": f"turn {i}"})
        messages.append({"role": "assistant", "content": content})
    return {"messages": messages}


def test_no_question_guard_below_streak_threshold() -> None:
    state = _q_state(["oke?", "gimana?"])
    assert _question_ending_note(state) == ""


def test_question_guard_fires_on_three_in_a_row() -> None:
    # Real finding via a real 2-session/20-turn run (2026-07-13): a
    # prompt-only cap on question-endings did not change behavior (19/20,
    # then 18/20 turns still ended in '?'), so this is computed in code
    # instead, mirroring _recent_name_usage_note's approach.
    state = _q_state(["oke?", "gimana?", "terus?"])
    note = _question_ending_note(state)
    assert "last 3" in note
    assert "Do NOT end this response with a question" in note


def test_question_guard_does_not_fire_when_streak_broken() -> None:
    state = _q_state(["oke.", "gimana?", "terus?"])
    assert _question_ending_note(state) == ""

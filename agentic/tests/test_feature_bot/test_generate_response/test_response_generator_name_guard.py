"""regression: LLM self-counting name usage across the system prompt proved
unreliable on real scripted-persona runs (2026-07-12), so the guard is
computed deterministically from conversation history instead."""

from __future__ import annotations

from agentic.agent.nodes.response_generator import (
    _looks_like_human_display_name,
    _memory_repetition_note,
    _question_ending_note,
    _recent_name_usage_note,
    _repetitive_opener_note,
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


def test_question_guard_exempts_reframe() -> None:
    # Real bug found via a real 20-turn run (2026-07-13): the router picked
    # reframe on the exact turn the streak guard also fired, and the model
    # dropped reframe.yaml's mandatory Socratic question to comply with the
    # guard -- silently defeating the technique that turn. The guard must
    # not fire when the technique's own question is the technique.
    state = _q_state(["oke?", "gimana?", "terus?"])
    state["cbt_node_active"] = "reframe"
    assert _question_ending_note(state) == ""


def test_question_guard_exempts_thought_record() -> None:
    state = _q_state(["oke?", "gimana?", "terus?"])
    state["cbt_node_active"] = "thought_record"
    assert _question_ending_note(state) == ""


def test_question_guard_still_fires_for_validate() -> None:
    # validate is the common case (4 of 5 guard-triggered turns in the same
    # 20-turn run) and its question is a style default, not the technique's
    # core mechanism, so the guard should still apply normally.
    state = _q_state(["oke?", "gimana?", "terus?"])
    state["cbt_node_active"] = "validate"
    note = _question_ending_note(state)
    assert "Do NOT end this response with a question" in note


def test_no_opener_guard_below_streak_threshold() -> None:
    state = _q_state(["Jadi kamu ngerasa gitu ya.", "Oh, jadi gitu."])
    assert _repetitive_opener_note(state) == ""


def test_opener_guard_fires_on_three_in_a_row() -> None:
    # Real finding via a real 20-turn run (2026-07-13): 12 of 19 AXIS turns
    # opened with "Jadi..."/"Oh, jadi..." to paraphrase the user back,
    # which read as templated despite the technique itself being valid.
    state = _q_state(
        [
            "Jadi revisian dosen itu ya yang bikin susah tidur.",
            "Oh, jadi bagian format sama pembahasan ya.",
            "Jadi kayak masih ada celah gitu ya rasanya.",
        ]
    )
    note = _repetitive_opener_note(state)
    assert "jadi" in note.lower()
    assert "last 3" in note


def test_opener_guard_does_not_fire_when_openers_vary() -> None:
    state = _q_state(
        [
            "Jadi revisian dosen itu ya yang bikin susah tidur.",
            "Berat banget rasanya kalau udah begini.",
            "Hmm, kedengarannya kayak lagi buntu ya.",
        ]
    )
    assert _repetitive_opener_note(state) == ""


def test_opener_guard_is_word_agnostic() -> None:
    # Deliberately not "jadi"/"oh" specific -- any repeated opener word
    # across the streak should trip the guard, not just the one found.
    state = _q_state(
        [
            "Duh, kedengarannya berat banget ya.",
            "Duh, itu pasti capek rasanya.",
            "Duh, wajar banget kalau ngerasa gitu.",
        ]
    )
    note = _repetitive_opener_note(state)
    assert "duh" in note.lower()


def _mem_state(*, understanding: dict | None, assistant_turns: list[str]) -> dict:
    messages = []
    for i, content in enumerate(assistant_turns):
        messages.append({"role": "user", "content": f"turn {i}"})
        messages.append({"role": "assistant", "content": content})
    return {"messages": messages, "user_understanding": understanding}


def test_no_memory_guard_when_understanding_missing() -> None:
    state = _mem_state(understanding=None, assistant_turns=["Gimana harimu?"])
    assert _memory_repetition_note(state) == ""


def test_no_memory_guard_when_insufficient_data() -> None:
    state = _mem_state(
        understanding={
            "insufficient_data": True,
            "grounding_experience": "dimarahi dosen pembimbing skripsi Pak Agung",
        },
        assistant_turns=["Cerita dong lagi kepikiran apa."],
    )
    assert _memory_repetition_note(state) == ""


def test_no_memory_guard_when_focus_too_thin() -> None:
    # Only one distinctive keyword ("capek") -- below the 2-keyword floor,
    # not specific enough to reliably signal an actual repeat.
    state = _mem_state(
        understanding={"grounding_experience": "capek", "active_pattern": None},
        assistant_turns=["Kayaknya capek banget ya belakangan ini."],
    )
    assert _memory_repetition_note(state) == ""


def test_no_memory_guard_when_no_overlap_with_recent_turns() -> None:
    state = _mem_state(
        understanding={
            "grounding_experience": "dimarahi dosen pembimbing skripsi Pak Agung waktu bimbingan",
            "active_pattern": None,
        },
        assistant_turns=["Gimana kabar tugas kelompok minggu ini?"],
    )
    assert _memory_repetition_note(state) == ""


def test_memory_guard_fires_on_grounding_experience_overlap() -> None:
    # Real risk once v3 dropped its 1-callback cap: the same
    # grounding_experience keeps getting surfaced turn after turn because
    # the underlying retrieved memory does not change between turns.
    state = _mem_state(
        understanding={
            "grounding_experience": "dimarahi dosen pembimbing skripsi Pak Agung waktu bimbingan",
            "active_pattern": None,
        },
        assistant_turns=["Kedengarannya masih kepikiran soal Pak Agung pas bimbingan itu ya."],
    )
    note = _memory_repetition_note(state)
    assert "Do not surface that same memory again" in note
    assert "agung" in note.lower()


def test_memory_guard_fires_on_active_pattern_overlap() -> None:
    state = _mem_state(
        understanding={
            "grounding_experience": None,
            "active_pattern": "kalau gagal sidang sekali berarti gagal selamanya",
        },
        assistant_turns=["Kalau sekali gagal sidang bukan berarti gagal selamanya kok."],
    )
    note = _memory_repetition_note(state)
    assert "Do not surface that same memory again" in note


def test_memory_guard_respects_lookback_window() -> None:
    # Overlap only in the 3rd-most-recent assistant turn; lookback is 2, so
    # this should not fire -- an old callback naturally ages out.
    state = _mem_state(
        understanding={
            "grounding_experience": "dimarahi dosen pembimbing skripsi Pak Agung waktu bimbingan",
            "active_pattern": None,
        },
        assistant_turns=[
            "Kedengarannya masih kepikiran soal Pak Agung pas bimbingan itu ya.",
            "Gimana kabar tugas kelompok minggu ini?",
            "Semoga revisinya lancar ya minggu ini.",
        ],
    )
    assert _memory_repetition_note(state) == ""

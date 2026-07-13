"""clarify"""

from __future__ import annotations

import json

import pytest

from agentic.agent.phq9.subgraph import phq9_subgraph_node
from agentic.agent.state import empty_conversation_state, empty_phq9_state
from agentic.tests.test_assessment.conftest import FakeLLM


def _state_for_item(*, user_text: str, language: str = "id"):
    state = empty_conversation_state(
        user_id="u1",
        session_id="s1",
        language_pref=language,
    )
    state["resolved_language"] = language
    state["current_message"] = user_text
    phq9 = empty_phq9_state()
    phq9["phase"] = "in_progress"  # type: ignore[assignment]
    phq9["language"] = language
    phq9["active_item"] = 1
    state["phq9_state"] = phq9
    return state


@pytest.mark.asyncio
async def test_explanation_request_uses_llm(fake_repo) -> None:
    # choose clarify
    judge_llm = FakeLLM(
        script=[
            json.dumps(
                {
                    "score": 0,
                    "confidence": 0.0,
                    "action": "clarify",
                    "next_item": None,
                    "rationale": "user_asked_meaning",
                }
            )
        ]
    )
    explanation_llm = FakeLLM(
        script=[
            "Maksudnya, aku pengen tahu seberapa sering dalam 2 minggu terakhir kamu merasa kurang tertarik atau kurang menikmati hal-hal yang biasanya kamu lakukan.\n\nKalau misalnya sempat ada hari-hari kamu jadi males/ga kepengen ngapa-ngapain, itu termasuk. Dari pilihan 0–3 tadi, yang paling mendekati yang mana?"
        ]
    )

    state = _state_for_item(user_text="jelasin dong maksudnya", language="id")
    out = await phq9_subgraph_node(
        state,
        repo=fake_repo,
        judge_llm=judge_llm,
        clarification_llm=explanation_llm,
    )

    phq9 = out["phq9_state"]
    assert phq9["phase"] == "awaiting_clar"
    assert phq9["awaiting_clarification"] is True
    assert "Maksudnya" in out.get("response_draft", "")
    assert "lebih cocok" not in out.get("response_draft", "")


@pytest.mark.asyncio
async def test_ambiguous_answer_still_uses_static_clarification(fake_repo) -> None:
    judge_llm = FakeLLM(
        script=[
            json.dumps(
                {
                    "score": 1,
                    "confidence": 0.2,
                    "action": "clarify",
                    "next_item": None,
                    "rationale": "ambiguous",
                }
            )
        ]
    )

    state = _state_for_item(user_text="ambig answer", language="id")
    out = await phq9_subgraph_node(
        state,
        repo=fake_repo,
        judge_llm=judge_llm,
        clarification_llm=None,
    )

    assert "lebih cocok" in out.get("response_draft", "")

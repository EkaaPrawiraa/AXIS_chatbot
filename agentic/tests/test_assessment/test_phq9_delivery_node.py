"""end2end tests"""

from __future__ import annotations

from typing import Any

import pytest

from agentic.agent.nodes.phq9_delivery import (
    WARMUP_TURNS_BEFORE_OFFER,
    phq9_delivery_node,
)
from agentic.agent.state import (
    ConversationState,
    empty_conversation_state,
    empty_phq9_state,
)
from agentic.assessment.phq9 import NUM_ITEMS



def _bootstrap_state(
    *,
    phase: str = "offer_pending",
    tier: str = "scheduled",
    session_turn: int = WARMUP_TURNS_BEFORE_OFFER,
    user_message: str = "",
    language: str = "id",
) -> ConversationState:
    state = empty_conversation_state(
        user_id="u1", session_id="s1", language_pref=language
    )
    state["session_turn"] = session_turn
    state["current_message"] = user_message
    state["resolved_language"] = language
    phq9 = empty_phq9_state()
    phq9["phase"] = phase  # type: ignore[assignment]
    phq9["tier"] = tier  # type: ignore[assignment]
    phq9["language"] = language
    state["phq9_state"] = phq9
    return state


async def _run(
    state: ConversationState,
    *,
    repo: Any,
    scorer_llm: Any | None = None,
    feedback_llm: Any | None = None,
):
    return await phq9_delivery_node(
        state,
        repo=repo,
        scorer_llm=scorer_llm,
        feedback_llm=feedback_llm,
    )


# skip klo error


class TestOfferPhases:
    @pytest.mark.asyncio
    async def test_warmup_holds_offer(self, fake_repo) -> None:
        state = _bootstrap_state(session_turn=0)
        out = await _run(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "offer_pending"
        assert "response_draft" not in out or not out.get("response_draft")

    @pytest.mark.asyncio
    async def test_offer_arms_response_generator_after_warmup(self, fake_repo) -> None:
        state = _bootstrap_state(session_turn=WARMUP_TURNS_BEFORE_OFFER)
        out = await _run(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "offer_pending"
        assert out["phq9_state"]["offer_armed"] is True
        assert "response_draft" not in out or not out.get("response_draft")

    @pytest.mark.asyncio
    async def test_event_tier_holds_until_session_ending(self, fake_repo) -> None:
        state = _bootstrap_state(tier="event")
        out = await _run(state, repo=fake_repo)
        # skip sess
        assert out["phq9_state"]["phase"] == "offer_pending"

    @pytest.mark.asyncio
    async def test_event_tier_arms_at_session_end(self, fake_repo) -> None:
        state = _bootstrap_state(tier="event")
        state["session_ending"] = True  # type: ignore[typeddict-unknown-key]
        out = await _run(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "offer_pending"
        assert out["phq9_state"]["offer_armed"] is True

    @pytest.mark.asyncio
    async def test_decline_acknowledged(self, fake_repo) -> None:
        state = _bootstrap_state(phase="offered", user_message="nanti aja")
        out = await _run(state, repo=fake_repo)
        assert out["phq9_state"]["phase"] == "declined"
        assert out["response_draft"]

    @pytest.mark.asyncio
    async def test_accept_starts_questionnaire(
        self, fake_repo, scorer_llm_factory
    ) -> None:
        state = _bootstrap_state(phase="offered", user_message="iya boleh")
        out = await _run(state, repo=fake_repo)
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "in_progress"
        assert phq9["active_item"] == 1
        assert "Pertanyaan 1" in out["response_draft"]


# inpro


class TestItemByItem:
    @pytest.mark.asyncio
    async def test_button_tap_advances_to_next_item(
        self, fake_repo, scorer_llm_factory
    ) -> None:
        state = _bootstrap_state(phase="in_progress", user_message="2")
        state["phq9_state"]["active_item"] = 1
        out = await _run(state, repo=fake_repo, scorer_llm=scorer_llm_factory())
        phq9 = out["phq9_state"]
        assert phq9["active_item"] == 2
        assert phq9["responses"][1]["score"] == 2
        assert phq9["responses"][1]["source"] == "button"
        assert "Pertanyaan 2" in out["response_draft"]

    @pytest.mark.asyncio
    async def test_text_answer_uses_llm_scorer(
        self, fake_repo, scorer_llm_factory
    ) -> None:
        # nggunin lmscore
        state = _bootstrap_state(
            phase="in_progress", user_message="iya, hampir setiap hari banget"
        )
        state["phq9_state"]["active_item"] = 1
        out = await _run(state, repo=fake_repo, scorer_llm=scorer_llm_factory())
        responses = out["phq9_state"]["responses"]
        assert responses[1]["source"] == "text_llm"
        assert responses[1]["score"] == 3

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_clarification(
        self, fake_repo, scorer_llm_factory
    ) -> None:
        state = _bootstrap_state(phase="in_progress", user_message="ambig answer")
        state["phq9_state"]["active_item"] = 4
        out = await _run(state, repo=fake_repo, scorer_llm=scorer_llm_factory())
        phq9 = out["phq9_state"]
        assert phq9["phase"] == "awaiting_clar"
        assert phq9["awaiting_clarification"] is True
        # skip clarif
        assert phq9["active_item"] == 4

    @pytest.mark.asyncio
    async def test_clarification_eventually_accepts_best_guess(
        self, fake_repo, scorer_llm_factory
    ) -> None:
        # skip low conf
        state = _bootstrap_state(phase="in_progress", user_message="ambig answer")
        state["phq9_state"]["active_item"] = 4
        out = await _run(state, repo=fake_repo, scorer_llm=scorer_llm_factory())
        assert out["phq9_state"]["phase"] == "awaiting_clar"

        # guess best.
        out["current_message"] = "ambig again"
        out2 = await _run(out, repo=fake_repo, scorer_llm=scorer_llm_factory())
        assert out2["phq9_state"]["active_item"] == 5
        assert 4 in out2["phq9_state"]["responses"]


# finalize


class TestFinalize:
    @pytest.mark.asyncio
    async def test_full_run_persists_result_and_clears_retry(
        self, fake_repo, scorer_llm_factory, feedback_llm
    ) -> None:
        state = _bootstrap_state(phase="in_progress")
        state["phq9_state"]["active_item"] = 1

        for item_id in range(1, NUM_ITEMS + 1):
            state["current_message"] = "1"
            state["phq9_state"]["active_item"] = item_id
            state = await _run(
                state,
                repo=fake_repo,
                scorer_llm=scorer_llm_factory(),
                feedback_llm=feedback_llm,
            )

        phq9 = state["phq9_state"]
        # 9 == 1, safety, phase ends, routes to session_end.
        assert phq9["phase"] == "deferred_crisis"
        assert phq9["last_total"] == NUM_ITEMS  # all answered with 1
        assert phq9["last_severity"] == "mild"
        assert phq9["item9_flagged"] is True  # item 9 == 1
        assert phq9["route_to_crisis_after"] is True
        assert fake_repo.state.saved_results, "result should be persisted"
        assert fake_repo.state.cleared_retries_for == ["u1"]
        assert state["safety_flag"] == "escalate"

    @pytest.mark.asyncio
    async def test_item9_zero_does_not_route_to_crisis(
        self, fake_repo, scorer_llm_factory, feedback_llm
    ) -> None:
        state = _bootstrap_state(phase="in_progress")
        for item_id in range(1, NUM_ITEMS + 1):
            # skip
            state["current_message"] = "0"
            state["phq9_state"]["active_item"] = item_id
            state = await _run(
                state,
                repo=fake_repo,
                scorer_llm=scorer_llm_factory(),
                feedback_llm=feedback_llm,
            )

        phq9 = state["phq9_state"]
        assert phq9["phase"] == "completed"
        assert phq9["item9_flagged"] is False
        assert phq9["route_to_crisis_after"] is False
        assert state.get("safety_flag") != "escalate"

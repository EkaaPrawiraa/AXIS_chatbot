"""test convo"""

from __future__ import annotations

import json

import pytest

from agentic.assessment.conversational_delivery import (
    CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT,
    build_acknowledgement,
    build_clarification,
    build_feedback_message,
    build_greeting,
    build_item_prompt,
    build_offer,
    score_text_response,
)
from agentic.assessment.phq9 import NUM_ITEMS, PHQ9Severity



class TestPromptBuilders:
    def test_greeting_has_phq9_reference_id(self) -> None:
        text = build_greeting("id")
        assert "PHQ-9" in text
        assert "9" in text

    def test_greeting_en_has_two_weeks_phrase(self) -> None:
        text = build_greeting("en")
        assert "two weeks" in text.lower()

    def test_offer_id_uses_indonesian(self) -> None:
        text = build_offer("id")
        assert "ngecek" in text or "ngobrol" in text

    def test_offer_en_uses_english(self) -> None:
        text = build_offer("en")
        assert "weeks" in text.lower()

    @pytest.mark.parametrize("item_id", range(1, NUM_ITEMS + 1))
    def test_item_prompt_includes_all_options_id(self, item_id: int) -> None:
        prompt = build_item_prompt(item_id, "id")
        for score in range(4):
            assert f"{score}." in prompt
        assert f"{item_id} dari {NUM_ITEMS}" in prompt

    @pytest.mark.parametrize("item_id", range(1, NUM_ITEMS + 1))
    def test_item_prompt_includes_all_options_en(self, item_id: int) -> None:
        prompt = build_item_prompt(item_id, "en")
        for score in range(4):
            assert f"{score}." in prompt
        assert f"{item_id} of {NUM_ITEMS}" in prompt

    def test_clarification_mentions_item_number(self) -> None:
        clar = build_clarification(5, "id", "kadang aja")
        assert "5" in clar

    def test_acknowledgement_advances_index(self) -> None:
        ack = build_acknowledgement(3, "id")
        assert "4" in ack


# free-scor


class TestScoreTextResponse:
    @pytest.mark.asyncio
    async def test_high_confidence_button_match(
        self, scorer_llm_factory
    ) -> None:
        llm = scorer_llm_factory()
        outcome = await score_text_response(
            item_id=1,
            user_text="hampir setiap hari",
            language="id",
            llm=llm,
        )
        assert outcome.score == 3
        assert outcome.confidence >= CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT
        assert outcome.needs_clarification is False

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_clarification(
        self, scorer_llm_factory
    ) -> None:
        llm = scorer_llm_factory()
        outcome = await score_text_response(
            item_id=1,
            user_text="ambig answer",
            language="id",
            llm=llm,
        )
        assert outcome.needs_clarification is True
        assert outcome.confidence < CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT

    @pytest.mark.asyncio
    async def test_malformed_llm_output_falls_through(self) -> None:
        from agentic.tests.test_assessment.conftest import FakeLLM

        llm = FakeLLM(script=["this is not json"])
        outcome = await score_text_response(
            item_id=2,
            user_text="not sure",
            language="en",
            llm=llm,
        )
        assert outcome.score == 0
        assert outcome.confidence == 0.0
        assert outcome.needs_clarification is True

    @pytest.mark.asyncio
    async def test_llm_failure_flagged_as_clarification(self) -> None:
        class BrokenLLM:
            async def ainvoke(self, _messages):
                raise RuntimeError("boom")

        outcome = await score_text_response(
            item_id=2,
            user_text="hello",
            language="en",
            llm=BrokenLLM(),
        )
        assert outcome.needs_clarification is True
        assert outcome.confidence == 0.0



class TestFeedback:
    @pytest.mark.asyncio
    async def test_feedback_returns_llm_output(self, feedback_llm) -> None:
        text = await build_feedback_message(
            total_score=6,
            severity=PHQ9Severity.MILD,
            item_scores=tuple([1] * 9),
            language="id",
            item9_flagged=False,
            llm=feedback_llm,
        )
        assert "PHQ-9" in text or "ringan" in text.lower()
        assert feedback_llm.calls, "feedback LLM should have been invoked"

    @pytest.mark.asyncio
    async def test_feedback_falls_back_when_llm_fails(self) -> None:
        class BrokenLLM:
            async def ainvoke(self, _messages):
                raise RuntimeError("nope")

        text = await build_feedback_message(
            total_score=12,
            severity=PHQ9Severity.MODERATE,
            item_scores=tuple([1, 2, 1, 2, 1, 2, 1, 1, 1]),
            language="id",
            item9_flagged=True,
            llm=BrokenLLM(),
        )
        assert "12" in text

    @pytest.mark.asyncio
    async def test_feedback_fallback_uses_screening_not_diagnosis(self) -> None:
        class BrokenLLM:
            async def ainvoke(self, _messages):
                raise RuntimeError("nope")

        text = await build_feedback_message(
            total_score=13,
            severity=PHQ9Severity.MODERATE,
            item_scores=tuple([1, 2, 1, 2, 1, 2, 1, 2, 1]),
            language="id",
            item9_flagged=True,
            llm=BrokenLLM(),
        )

        lowered = text.lower()
        assert "bukan diagnosis" in lowered
        assert "skrining phq-9" in lowered
        assert "depresi" not in lowered

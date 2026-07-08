"""test agentic.assessment.phq9"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agentic.assessment.phq9 import (
    DEFAULT_LANGUAGE,
    ITEM9_INDEX_ZERO_BASED,
    ITEMS_EN,
    ITEMS_ID,
    NUM_ITEMS,
    OPTION_LABELS_EN,
    OPTION_LABELS_ID,
    PHQ9Response,
    PHQ9Severity,
    ResponseSource,
    compute_severity,
    detect_language_lightweight,
    get_items,
    get_option_labels,
    item_text,
    options_with_scores,
    resolve_language,
    score_phq9,
    to_storage_payload,
)



class TestConstants:
    def test_item_count_is_nine_in_both_languages(self) -> None:
        assert len(ITEMS_ID) == NUM_ITEMS == len(ITEMS_EN) == 9

    def test_option_labels_have_four_levels(self) -> None:
        assert len(OPTION_LABELS_ID) == 4
        assert len(OPTION_LABELS_EN) == 4

    def test_item9_index_matches_one_based(self) -> None:
        assert ITEM9_INDEX_ZERO_BASED == 8



class TestSeverity:
    @pytest.mark.parametrize(
        "total, expected",
        [
            (0, PHQ9Severity.MINIMAL),
            (4, PHQ9Severity.MINIMAL),
            (5, PHQ9Severity.MILD),
            (9, PHQ9Severity.MILD),
            (10, PHQ9Severity.MODERATE),
            (14, PHQ9Severity.MODERATE),
            (15, PHQ9Severity.MODERATELY_SEVERE),
            (19, PHQ9Severity.MODERATELY_SEVERE),
            (20, PHQ9Severity.SEVERE),
            (27, PHQ9Severity.SEVERE),
        ],
    )
    def test_band_boundaries(self, total: int, expected: PHQ9Severity) -> None:
        assert compute_severity(total) is expected

    @pytest.mark.parametrize("bad", [-1, 28, 100])
    def test_out_of_range_raises(self, bad: int) -> None:
        with pytest.raises(ValueError):
            compute_severity(bad)



class TestResponseDataclass:
    def test_valid_button_response(self) -> None:
        r = PHQ9Response(item_id=1, score=2, source=ResponseSource.BUTTON)
        assert r.item_id == 1 and r.score == 2

    def test_text_llm_with_confidence(self) -> None:
        r = PHQ9Response(
            item_id=3,
            score=1,
            source=ResponseSource.TEXT_LLM,
            raw_text="kadang aja",
            confidence=0.8,
        )
        assert r.confidence == 0.8

    @pytest.mark.parametrize("bad_id", [0, -1, 10, 100])
    def test_invalid_item_id_raises(self, bad_id: int) -> None:
        with pytest.raises(ValueError):
            PHQ9Response(item_id=bad_id, score=0, source=ResponseSource.BUTTON)

    @pytest.mark.parametrize("bad_score", [-1, 4, 99])
    def test_invalid_score_raises(self, bad_score: int) -> None:
        with pytest.raises(ValueError):
            PHQ9Response(item_id=1, score=bad_score, source=ResponseSource.BUTTON)

    @pytest.mark.parametrize("bad_conf", [-0.1, 1.1, 5.0])
    def test_invalid_confidence_raises(self, bad_conf: float) -> None:
        with pytest.raises(ValueError):
            PHQ9Response(
                item_id=1,
                score=0,
                source=ResponseSource.TEXT_LLM,
                confidence=bad_conf,
            )


# score_phq9


def _all_button_responses(scores: list[int]) -> list[PHQ9Response]:
    return [
        PHQ9Response(item_id=i + 1, score=scores[i], source=ResponseSource.BUTTON)
        for i in range(NUM_ITEMS)
    ]


class TestScorePhq9:
    def test_total_and_severity_minimal(self) -> None:
        result = score_phq9(
            user_id="u1",
            session_id="s1",
            responses=_all_button_responses([0] * 9),
            language="id",
        )
        assert result.total_score == 0
        assert result.severity is PHQ9Severity.MINIMAL
        assert result.item9_score == 0
        assert result.item9_flagged is False

    def test_total_and_severity_severe(self) -> None:
        result = score_phq9(
            user_id="u1",
            session_id="s1",
            responses=_all_button_responses([3] * 9),
            language="id",
        )
        assert result.total_score == 27
        assert result.severity is PHQ9Severity.SEVERE
        assert result.item9_flagged is True

    def test_delta_computation_when_previous_total_provided(self) -> None:
        result = score_phq9(
            user_id="u1",
            session_id="s1",
            responses=_all_button_responses([2] * 9),
            language="id",
            previous_total=10,
        )
        assert result.total_score == 18
        assert result.delta_from_previous == 8

    def test_no_delta_when_no_previous(self) -> None:
        result = score_phq9(
            user_id="u1",
            session_id="s1",
            responses=_all_button_responses([1] * 9),
            language="id",
        )
        assert result.delta_from_previous is None

    def test_missing_responses_raises(self) -> None:
        partial = _all_button_responses([1] * 9)[:-1]
        with pytest.raises(ValueError, match="missing"):
            score_phq9(
                user_id="u1",
                session_id="s1",
                responses=partial,
                language="id",
            )

    def test_duplicate_responses_raises(self) -> None:
        rs = _all_button_responses([1] * 9)
        rs.append(rs[0])
        with pytest.raises(ValueError, match="duplicate"):
            score_phq9(
                user_id="u1",
                session_id="s1",
                responses=rs,
                language="id",
            )

    def test_item9_flag_only_when_nonzero(self) -> None:
        scores = [0] * 9
        scores[8] = 1
        result = score_phq9(
            user_id="u",
            session_id="s",
            responses=_all_button_responses(scores),
            language="en",
        )
        assert result.item9_flagged is True
        assert result.total_score == 1
        assert result.severity is PHQ9Severity.MINIMAL

    def test_storage_payload_shape(self) -> None:
        result = score_phq9(
            user_id="u",
            session_id="s",
            responses=_all_button_responses([2] * 9),
            language="id",
            previous_total=10,
            administered_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
        )
        payload = to_storage_payload(result)
        assert payload["instrument"] == "PHQ-9"
        assert payload["score"] == 18.0
        assert payload["delta_from_prev"] == 8.0
        assert payload["item_responses"] == {str(i): 2 for i in range(1, 10)}
        assert payload["administered_by"] == "chatbot"



class TestLocalization:
    def test_get_items_id(self) -> None:
        assert get_items("id") == ITEMS_ID

    def test_get_items_en(self) -> None:
        assert get_items("en") == ITEMS_EN

    def test_get_items_unknown_falls_back(self) -> None:
        assert get_items("xx") == ITEMS_ID  # default is id

    def test_options_with_scores(self) -> None:
        opts = options_with_scores("id")
        assert opts[0] == (0, OPTION_LABELS_ID[0])
        assert opts[3] == (3, OPTION_LABELS_ID[3])

    def test_item_text(self) -> None:
        assert item_text(1, "id") == ITEMS_ID[0]
        assert item_text(9, "en") == ITEMS_EN[8]

    @pytest.mark.parametrize("bad_id", [0, 10, -1])
    def test_item_text_out_of_range(self, bad_id: int) -> None:
        with pytest.raises(ValueError):
            item_text(bad_id, "id")



class TestLanguageDetect:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("saya merasa sangat lelah", "id"),
            ("aku tidak tahu kenapa", "id"),
            ("I am tired and sad", "en"),
            ("the weather is fine", "en"),
            ("", DEFAULT_LANGUAGE),
        ],
    )
    def test_lightweight(self, text: str, expected: str) -> None:
        assert detect_language_lightweight(text) == expected

    def test_resolve_prefers_user_pref(self) -> None:
        assert resolve_language(
            user_pref="en", recent_messages=["saya sedih banget"]
        ) == "en"

    def test_resolve_falls_back_to_detection(self) -> None:
        assert resolve_language(
            user_pref=None, recent_messages=["saya capek banget"]
        ) == "id"

    def test_resolve_falls_back_to_default(self) -> None:
        assert resolve_language(user_pref=None, recent_messages=[]) == DEFAULT_LANGUAGE

    def test_resolve_invalid_pref_falls_through(self) -> None:
        # block it
        assert resolve_language(
            user_pref="zh", recent_messages=["I am tired"]
        ) == "en"

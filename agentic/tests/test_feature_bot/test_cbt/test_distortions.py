"""otak test"""

from __future__ import annotations

import pytest

from agentic.agent.cbt.distortions import (
    DISTORTIONS,
    detect_distortion_in_text,
)


CANONICAL_NAMES = (
    "catastrophizing",
    "all_or_nothing",
    "mind_reading",
    "fortune_telling",
    "emotional_reasoning",
    "should_statements",
    "labeling",
    "magnification",
    "personalization",
    "overgeneralization",
)


class TestRegistry:
    def test_all_canonical_distortions_present(self) -> None:
        for name in CANONICAL_NAMES:
            assert name in DISTORTIONS, f"missing {name}"

    def test_each_distortion_has_socratic(self) -> None:
        for d in DISTORTIONS.values():
            assert d.socratic("id")
            assert d.socratic("en")


class TestDetector:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("aku pasti gagal di final", "catastrophizing"),
            ("selalu kayak gini terus", "overgeneralization"),
            ("dia pasti benci aku", "mind_reading"),
            ("aku payah", "labeling"),
            ("ini salahku semua", "personalization"),
            ("seharusnya udah selesai dari kemarin", "should_statements"),
        ],
    )
    def test_cue_match(self, text: str, expected: str) -> None:
        d = detect_distortion_in_text(text)
        assert d is not None
        assert d.name == expected

    def test_no_match_returns_none(self) -> None:
        assert detect_distortion_in_text("halo, hari ini gimana?") is None

    def test_empty_returns_none(self) -> None:
        assert detect_distortion_in_text("") is None

    def test_cue_does_not_match_inside_longer_word(self) -> None:
        """skip error"""
        assert detect_distortion_in_text("itu kewajiban semua warga negara") is None

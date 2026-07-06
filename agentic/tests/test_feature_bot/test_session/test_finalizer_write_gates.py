"""
Regression tests for the per-node-type write gates in finalizer_factory.py.

Before this change, only Experience had a real significance floor;
Emotion and Behavior had no importance-based gate at all (any non-empty
text got written), and Thought/Trigger used purely structural proxies
(text length, pronoun presence) instead of the significance-like signal
the extractor already emits. See docs/importantS/analisis_memory_write_gating.md.

These tests exercise the pure `_should_write_*` predicates directly --
no DB, no LLM -- so they run fast and pin the exact threshold behavior.
"""

from __future__ import annotations

from agentic.agent.session.finalizer_factory import (
    _should_write_behavior,
    _should_write_emotion,
    _should_write_experience,
    _should_write_thought,
    _should_write_trigger,
)


class TestExperienceGate:
    """Unchanged behavior -- the one gate that already worked correctly."""

    def test_low_significance_rejected(self) -> None:
        assert not _should_write_experience(
            {"description": "makan siang biasa", "significance": 0.2, "valence": 0.1}
        )

    def test_high_significance_accepted(self) -> None:
        assert _should_write_experience(
            {"description": "putus sama pacar", "significance": 0.8, "valence": -0.7}
        )

    def test_mild_significance_with_strong_valence_accepted(self) -> None:
        assert _should_write_experience(
            {"description": "dimarahin dosen", "significance": 0.35, "valence": -0.7}
        )


class TestEmotionGate:
    """New gate -- previously ANY non-empty label+source_text wrote unconditionally."""

    def test_low_intensity_rejected(self) -> None:
        assert not _should_write_emotion(
            {"label": "kesel", "source_text": "agak kesel dikit", "intensity": 0.15}
        )

    def test_moderate_intensity_accepted(self) -> None:
        assert _should_write_emotion(
            {"label": "cemas", "source_text": "cemas banget", "intensity": 0.6}
        )

    def test_missing_intensity_defaults_to_passing(self) -> None:
        """Missing field defaults to 0.5 (passes) so a transient LLM
        omission doesn't silently drop the write -- only an explicit
        low value should reject."""
        assert _should_write_emotion({"label": "sedih", "source_text": "sedih hari ini"})

    def test_empty_label_rejected(self) -> None:
        assert not _should_write_emotion({"label": "", "source_text": "sedih", "intensity": 0.9})


class TestBehaviorGate:
    """New gate -- previously ANY non-empty description wrote unconditionally."""

    def test_low_significance_rejected(self) -> None:
        assert not _should_write_behavior(
            {"description": "scroll hp bentar", "significance": 0.2}
        )

    def test_high_significance_accepted(self) -> None:
        assert _should_write_behavior(
            {"description": "ga keluar kamar 3 hari", "significance": 0.8}
        )


class TestThoughtGate:
    def test_short_generic_rejected(self) -> None:
        assert not _should_write_thought({"content": "oke sip", "believability": 0.8})

    def test_long_enough_with_pronoun_and_decent_believability_accepted(self) -> None:
        assert _should_write_thought(
            {"content": "aku ngerasa aku emang ga akan pernah bisa", "believability": 0.7}
        )

    def test_near_zero_believability_rejected_even_if_structurally_ok(self) -> None:
        """A stray, barely-held hedge shouldn't accumulate as a durable
        cognition just because it's long enough and mentions 'aku'."""
        assert not _should_write_thought(
            {
                "content": "aku kayaknya cuma bercanda doang sih tadi",
                "believability": 0.1,
            }
        )


class TestTriggerGate:
    def test_short_description_rejected(self) -> None:
        assert not _should_write_trigger({"description": "ujian", "significance": 0.9})

    def test_low_significance_rejected_even_if_long_enough(self) -> None:
        assert not _should_write_trigger(
            {"description": "ujian kimia minggu depan", "significance": 0.2}
        )

    def test_decent_length_and_significance_accepted(self) -> None:
        assert _should_write_trigger(
            {"description": "sidang TA bulan depan", "significance": 0.7}
        )

"""test all"""

from __future__ import annotations

from agentic.agent.session.finalizer_factory import (
    _safe_iso_datetime,
    _should_write_behavior,
    _should_write_emotion,
    _should_write_experience,
    _should_write_thought,
    _should_write_trigger,
)


class TestExperienceGate:
    """ubah behvior ini"""

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
    """24/7 ngoding."""

    def test_low_intensity_rejected(self) -> None:
        assert not _should_write_emotion(
            {"label": "kesel", "source_text": "agak kesel dikit", "intensity": 0.15}
        )

    def test_moderate_intensity_accepted(self) -> None:
        assert _should_write_emotion(
            {"label": "cemas", "source_text": "cemas banget", "intensity": 0.6}
        )

    def test_missing_intensity_defaults_to_passing(self) -> None:
        """skip"""
        assert _should_write_emotion({"label": "sedih", "source_text": "sedih hari ini"})

    def test_empty_label_rejected(self) -> None:
        assert not _should_write_emotion({"label": "", "source_text": "sedih", "intensity": 0.9})


class TestBehaviorGate:
    """24/7 ngoding."""

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
        """buat nyimpan config"""
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


class TestSafeIsoDatetime:
    """regression: extractor, non-ISO, Neo4j, datetime, crash, whole, Experience, write"""

    def test_valid_iso_string_passes_through(self) -> None:
        assert _safe_iso_datetime("2026-07-10T12:00:00+00:00", fallback="FALLBACK") == "2026-07-10T12:00:00+00:00"

    def test_unknown_placeholder_falls_back(self) -> None:
        assert _safe_iso_datetime("UNKNOWN", fallback="FALLBACK") == "FALLBACK"

    def test_freeform_text_falls_back(self) -> None:
        assert _safe_iso_datetime("beberapa minggu yang lalu", fallback="FALLBACK") == "FALLBACK"

    def test_none_falls_back(self) -> None:
        assert _safe_iso_datetime(None, fallback="FALLBACK") == "FALLBACK"

    def test_empty_string_falls_back(self) -> None:
        assert _safe_iso_datetime("", fallback="FALLBACK") == "FALLBACK"

    def test_z_suffix_iso_string_passes_through(self) -> None:
        # emits Z, not +00:00
        assert _safe_iso_datetime("2026-07-10T12:00:00Z", fallback="FALLBACK") == "2026-07-10T12:00:00Z"

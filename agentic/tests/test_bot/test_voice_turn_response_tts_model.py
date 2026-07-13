"""tts_model constrained to TTSModelChoice"""
from __future__ import annotations

from agentic.gateway.model.chat import VoiceTurnResponse


def test_arbitrary_provider_model_string_does_not_raise() -> None:
    # tts_model typo
    resp = VoiceTurnResponse(tts_model="gemini_tts")
    assert resp.tts_model == "gemini_tts"


def test_real_gemini_tier_model_id_does_not_raise() -> None:
    resp = VoiceTurnResponse(tts_model="gemini-2.5-flash-preview-tts")
    assert resp.tts_model == "gemini-2.5-flash-preview-tts"


def test_legacy_literal_values_still_accepted() -> None:
    for value in ("v2_5_turbo", "v3", "openai_tts1"):
        resp = VoiceTurnResponse(tts_model=value)
        assert resp.tts_model == value


def test_none_is_still_accepted() -> None:
    resp = VoiceTurnResponse(tts_model=None)
    assert resp.tts_model is None

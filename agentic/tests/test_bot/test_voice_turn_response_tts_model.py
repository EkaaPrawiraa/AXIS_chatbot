"""
Regression test for the exact production crash: VoiceTurnResponse.tts_model
constrained to TTSModelChoice rejected "gemini_tts" with a pydantic
literal_error, 400-ing every /chat/invoke response where the Gemini TTS
fallback tier fired (i.e. whenever both ElevenLabs and OpenAI had
failed) -- which meant no audio reached the client at all, not even a
degraded one, since the response itself never serialized.
"""
from __future__ import annotations

from agentic.gateway.model.chat import VoiceTurnResponse


def test_arbitrary_provider_model_string_does_not_raise() -> None:
    # Must not raise -- this exact value crashed every response before
    # the fix (tts_model was typed as the request-side TTSModelChoice
    # literal, which never included the fallback-provider labels).
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

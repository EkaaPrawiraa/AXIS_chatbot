"""fix"""
from __future__ import annotations

from agentic.gateway.model.chat import SynthesizeSpeechRequest, VoiceTurnRequest


def test_short_tier_alias_accepted_by_synthesize_request() -> None:
    req = SynthesizeSpeechRequest(text="halo", tts_model="gemini-2.5-pro-tts")
    assert req.tts_model == "gemini-2.5-pro-tts"


def test_all_three_short_aliases_accepted() -> None:
    for value in ("gemini-3.1-flash-tts", "gemini-2.5-pro-tts", "gemini-3.5-flash-tts"):
        req = SynthesizeSpeechRequest(text="halo", tts_model=value)
        assert req.tts_model == value


def test_full_preview_ids_still_accepted() -> None:
    for value in (
        "gemini-3.1-flash-tts-preview",
        "gemini-2.5-pro-preview-tts",
        "gemini-3.5-flash-preview-tts",
    ):
        req = SynthesizeSpeechRequest(text="halo", tts_model=value)
        assert req.tts_model == value


def test_voice_turn_request_also_accepts_short_alias() -> None:
    req = VoiceTurnRequest(tts_model="gemini-3.5-flash-tts")
    assert req.tts_model == "gemini-3.5-flash-tts"

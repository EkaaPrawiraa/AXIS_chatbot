"""
Regression test for the exact production crash on /voice/synthesize:

    validation error ... tts_model ... Input should be 'v2_5_turbo',
    'v3', 'openai_tts1', 'gemini-3.1-flash-tts-preview',
    'gemini-2.5-pro-preview-tts' or 'gemini-2.5-flash-preview-tts'
    [input_value='gemini-2.5-pro-tts']

The frontend's Settings tier+gender picker sends the SHORT tier ids
(e.g. "gemini-2.5-pro-tts") -- agentic.config.gemini_tts_tiers.
resolve_gemini_tier() already accepts these as aliases for the real
model ids, but that alias resolution only runs AFTER pydantic
validation, so a request using the short form 422'd before it ever
reached that logic. Fixed by adding the short forms directly to the
TTSModelChoice literal in agent/state.py.
"""
from __future__ import annotations

from agentic.gateway.model.chat import SynthesizeSpeechRequest, VoiceTurnRequest


def test_short_tier_alias_accepted_by_synthesize_request() -> None:
    req = SynthesizeSpeechRequest(text="halo", tts_model="gemini-2.5-pro-tts")
    assert req.tts_model == "gemini-2.5-pro-tts"


def test_all_three_short_aliases_accepted() -> None:
    for value in ("gemini-3.1-flash-tts", "gemini-2.5-pro-tts", "gemini-2.5-flash-tts"):
        req = SynthesizeSpeechRequest(text="halo", tts_model=value)
        assert req.tts_model == value


def test_full_preview_ids_still_accepted() -> None:
    for value in (
        "gemini-3.1-flash-tts-preview",
        "gemini-2.5-pro-preview-tts",
        "gemini-2.5-flash-preview-tts",
    ):
        req = SynthesizeSpeechRequest(text="halo", tts_model=value)
        assert req.tts_model == value


def test_voice_turn_request_also_accepts_short_alias() -> None:
    req = VoiceTurnRequest(tts_model="gemini-2.5-flash-tts")
    assert req.tts_model == "gemini-2.5-flash-tts"

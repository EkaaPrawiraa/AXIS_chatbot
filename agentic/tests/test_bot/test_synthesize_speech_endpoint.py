"""
Regression tests for ChatGraphService.synthesize_speech (the stateless
/voice/synthesize endpoint used by the chat "Play" message action and the
profile page's voice preview).

Context: this endpoint used to duplicate an OLDER, ElevenLabs->OpenAI-only
version of the TTS fallback chain that never got the LLM_PROVIDER/Gemini
redesign applied to the in-turn text_to_speech_node -- so a caller picking
a Gemini voice character (a raw prebuilt voice name like "Enceladus", sent
straight through as voice_id per VoiceCatalog.get()'s "unknown voice_id"
fallback path) never actually reached Gemini here: ElevenLabs would reject
the unknown voice, and it would then always fall to OpenAI. It also
collapsed any Gemini tts_model alias (e.g. "gemini-2.5-pro-tts") down to a
hardcoded ElevenLabs "v2_5_turbo" mode, discarding the caller's tier choice
entirely. Fixed by routing through the same run_tts_fallback_chain the
chat-turn node uses.
"""
from __future__ import annotations

import pytest

from agentic.agent.nodes import text_to_speech as tts_module
from agentic.gateway.model import SynthesizeSpeechRequest
from agentic.gateway.service.chat_graph import ChatGraphService

from agentic.tests.test_feature_bot.test_voice.conftest import (
    FakeElevenLabsTTS,
    FakeGeminiTTS,
    FakeOpenAITTS,
)


@pytest.fixture
def service() -> ChatGraphService:
    return ChatGraphService()


async def _no_op_tag_injection(text, *, llm=None):
    return text


def _patch_providers(monkeypatch, *, elevenlabs, openai_tts, gemini_tts):
    monkeypatch.setattr(tts_module, "ElevenLabsClient", lambda **_: elevenlabs)
    monkeypatch.setattr(tts_module, "OpenAITTSClient", lambda **_: openai_tts)
    monkeypatch.setattr(tts_module, "GeminiTTSClient", lambda **_: gemini_tts)
    # Whenever a test's ElevenLabs fake fails and the Gemini tier is
    # actually reached, _try_gemini now also calls _inject_gemini_audio_tags
    # (a real LLM call by default) -- stub it out so these tests stay
    # hermetic and don't hit the network.
    monkeypatch.setattr(tts_module, "_inject_gemini_audio_tags", _no_op_tag_injection)


class TestSynthesizeSpeechGeminiVoiceCharacter:
    @pytest.mark.asyncio
    async def test_raw_gemini_voice_id_reaches_gemini_when_elevenlabs_fails(
        self, service, monkeypatch,
    ) -> None:
        elevenlabs = FakeElevenLabsTTS(error="voice_id_not_configured")
        openai_tts = FakeOpenAITTS(error="should not be needed")
        gemini_tts = FakeGeminiTTS(error=None)
        _patch_providers(
            monkeypatch, elevenlabs=elevenlabs, openai_tts=openai_tts, gemini_tts=gemini_tts,
        )
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        response = await service.synthesize_speech(
            SynthesizeSpeechRequest(
                text="Hai, aku AXIS.",
                voice_id="Enceladus",
                tts_model="gemini-2.5-pro-tts",
                language_pref="id",
            )
        )

        assert response.tts_provider == "gemini_tts"
        assert response.audio_output_base64 is not None
        assert response.voice_error is None
        # ElevenLabs was tried and failed, but OpenAI must never have been
        # reached -- Gemini succeeded first per LLM_PROVIDER=gemini.
        assert openai_tts.calls == []
        assert gemini_tts.calls

    @pytest.mark.asyncio
    async def test_gemini_tier_alias_is_not_collapsed_to_elevenlabs_mode(
        self, service, monkeypatch,
    ) -> None:
        """The tts_model the caller picked (a Gemini tier alias) must reach
        resolve_gemini_tier as-is, not get discarded as "v2_5_turbo"."""
        elevenlabs = FakeElevenLabsTTS(error="voice_id_not_configured")
        openai_tts = FakeOpenAITTS(error="should not be needed")
        gemini_tts = FakeGeminiTTS(error=None)
        _patch_providers(
            monkeypatch, elevenlabs=elevenlabs, openai_tts=openai_tts, gemini_tts=gemini_tts,
        )
        monkeypatch.setenv("LLM_PROVIDER", "gemini")

        response = await service.synthesize_speech(
            SynthesizeSpeechRequest(
                text="Hai, aku AXIS.",
                voice_id="Enceladus",
                tts_model="gemini-2.5-pro-tts",
                language_pref="id",
            )
        )

        assert gemini_tts.calls
        assert gemini_tts.calls[0]["model"] == "gemini-2.5-pro-preview-tts"

    @pytest.mark.asyncio
    async def test_falls_back_to_openai_when_llm_provider_is_openai(
        self, service, monkeypatch,
    ) -> None:
        elevenlabs = FakeElevenLabsTTS(error="voice_id_not_configured")
        openai_tts = FakeOpenAITTS(error=None)
        gemini_tts = FakeGeminiTTS(error="should not be needed")
        _patch_providers(
            monkeypatch, elevenlabs=elevenlabs, openai_tts=openai_tts, gemini_tts=gemini_tts,
        )
        monkeypatch.setenv("LLM_PROVIDER", "openai")

        response = await service.synthesize_speech(
            SynthesizeSpeechRequest(
                text="Hai, aku AXIS.",
                voice_id="alloy",
                tts_model="v2_5_turbo",
                language_pref="id",
            )
        )

        assert response.tts_provider == "openai_tts1"
        assert response.audio_output_base64 is not None
        assert gemini_tts.calls == []

    @pytest.mark.asyncio
    async def test_openai_tts1_sentinel_skips_elevenlabs_and_gemini_entirely(
        self, service, monkeypatch,
    ) -> None:
        elevenlabs = FakeElevenLabsTTS(error=None)
        openai_tts = FakeOpenAITTS(error=None)
        gemini_tts = FakeGeminiTTS(error=None)
        _patch_providers(
            monkeypatch, elevenlabs=elevenlabs, openai_tts=openai_tts, gemini_tts=gemini_tts,
        )

        response = await service.synthesize_speech(
            SynthesizeSpeechRequest(
                text="Hai, aku AXIS.",
                voice_id="alloy",
                tts_model="openai_tts1",
                language_pref="id",
            )
        )

        assert response.tts_provider == "openai_tts1"
        assert elevenlabs.calls == []
        assert gemini_tts.calls == []

    @pytest.mark.asyncio
    async def test_response_is_a_single_audio_blob_not_a_streaming_generator(
        self, service, monkeypatch,
    ) -> None:
        """streaming must be forced off for this stateless single-shot
        endpoint -- a generator can't be base64-encoded as a whole, so
        leaving streaming on (as the in-turn node does for v2_5_turbo)
        would silently return no audio with no error."""
        elevenlabs = FakeElevenLabsTTS(error=None)
        openai_tts = FakeOpenAITTS()
        gemini_tts = FakeGeminiTTS()
        _patch_providers(
            monkeypatch, elevenlabs=elevenlabs, openai_tts=openai_tts, gemini_tts=gemini_tts,
        )

        response = await service.synthesize_speech(
            SynthesizeSpeechRequest(
                text="Hai, aku AXIS.",
                voice_id="alloy",
                tts_model="v2_5_turbo",
                language_pref="id",
            )
        )

        assert response.tts_provider == "elevenlabs"
        assert response.audio_output_base64 is not None

"""sksng_speech"""
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
    # inject_gemini_audio_tags
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
        # skip
        assert openai_tts.calls == []
        assert gemini_tts.calls

    @pytest.mark.asyncio
    async def test_gemini_tier_alias_is_not_collapsed_to_elevenlabs_mode(
        self, service, monkeypatch,
    ) -> None:
        """skip tier"""
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
        """skip stream"""
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

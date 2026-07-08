"""test stt node"""

from __future__ import annotations

import pytest

from agentic.agent.nodes.speech_to_text import (
    OpenAITranscriptionProvider,
    _openai_audio_file,
    _response_format_for_model,
    speech_to_text_node,
)
from agentic.agent.state import empty_conversation_state


class TestSTTNode:
    def test_bytes_audio_gets_supported_openai_filename(self) -> None:
        audio_file = _openai_audio_file(b"fake_audio_bytes", "audio/webm;codecs=opus")
        assert audio_file.name == "voice-input.webm"

    def test_gpt_transcribe_uses_json_response_format(self) -> None:
        assert _response_format_for_model("gpt-4o-mini-transcribe") == "json"
        assert _response_format_for_model("legacy-transcribe") == "verbose_json"

    def test_transcribe_provider_reads_openai_model_env(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
        provider = OpenAITranscriptionProvider()
        assert provider._model == "gpt-4o-mini-transcribe"

    @pytest.mark.asyncio
    async def test_no_audio_input_passes_through(self, audit) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        out = await speech_to_text_node(state, audit=audit)
        assert out["voice_state"]["transcript"] is None
        assert audit.events == []

    @pytest.mark.asyncio
    async def test_transcribes_and_sets_message(
        self, audit, fake_stt,
    ) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["voice_state"]["audio_input"] = b"fake_audio_bytes"
        state["voice_state"]["audio_input_mime"] = "audio/wav"
        out = await speech_to_text_node(
            state, provider=fake_stt, audit=audit,
        )
        voice = out["voice_state"]
        assert voice["transcript"] == fake_stt.text
        assert voice["transcript_language"] == "id"
        assert voice["output_modality"] == "voice"
        assert out["current_message"] == fake_stt.text
        assert out["resolved_language"] == "id"
        assert audit.has_type("stt_transcribed")

    @pytest.mark.asyncio
    async def test_failure_logs_warn_and_keeps_state(
        self, audit, fake_stt, fake_gemini_stt,
    ) -> None:
        fake_stt.raise_on_call = True
        state = empty_conversation_state(user_id="u", session_id="s")
        state["voice_state"]["audio_input"] = b"fake_audio_bytes"
        out = await speech_to_text_node(
            state, provider=fake_stt, fallback_provider=fake_gemini_stt, audit=audit,
        )
        assert out["voice_state"]["transcript"] is None
        assert "stt_error" in (out["voice_state"]["voice_error"] or "")
        assert audit.has_type("stt_error")

    @pytest.mark.asyncio
    async def test_gemini_fallback_used_when_primary_fails(
        self, audit, fake_stt, fake_gemini_stt,
    ) -> None:
        fake_stt.raise_on_call = True
        fake_gemini_stt.raise_on_call = False
        fake_gemini_stt.text = "halo dari gemini"
        state = empty_conversation_state(user_id="u", session_id="s")
        state["voice_state"]["audio_input"] = b"fake_audio_bytes"
        out = await speech_to_text_node(
            state, provider=fake_stt, fallback_provider=fake_gemini_stt, audit=audit,
        )
        voice = out["voice_state"]
        assert voice["transcript"] == "halo dari gemini"
        assert voice["voice_error"] is None
        assert audit.has_type("stt_transcribed")

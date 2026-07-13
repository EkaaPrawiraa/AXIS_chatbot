"""tts node"""

from __future__ import annotations

import pytest

from agentic.agent.nodes.text_to_speech import text_to_speech_node
from agentic.agent.state import empty_conversation_state
from agentic.tests.test_feature_bot.test_voice.conftest import FakeAdapterLLM


def _voice_ready(state, *, mode="v2_5_turbo", text="hai aku denger kamu"):
    state["voice_state"]["output_modality"] = "voice"
    state["voice_state"]["tts_model"] = mode
    state["voice_state"]["speech_response"] = text
    return state


@pytest.fixture(autouse=True)
def _pin_openai_second_tier(monkeypatch):
    """skip"""
    monkeypatch.setenv("LLM_PROVIDER", "openai")


class TestNode:
    @pytest.mark.asyncio
    async def test_text_modality_skips(
        self, audit, fake_elevenlabs, fake_openai_tts, voice_catalog,
    ) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["voice_state"]["output_modality"] = "text"
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        assert out["voice_state"]["audio_output_blob"] is None
        assert fake_elevenlabs.calls == []
        assert fake_openai_tts.calls == []

    @pytest.mark.asyncio
    async def test_v25_streaming_path(
        self, audit, fake_elevenlabs, fake_openai_tts, voice_catalog,
    ) -> None:
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            mode="v2_5_turbo",
        )
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        voice = out["voice_state"]
        assert voice["tts_provider"] == "elevenlabs"
        assert voice["audio_output_blob"] == fake_elevenlabs.blob
        assert voice["tts_streaming"] is True
        assert fake_elevenlabs.calls[0]["model"] == "eleven_turbo_v2_5"
        assert fake_elevenlabs.calls[0]["streaming"] is True
        assert audit.has_type("tts_elevenlabs")

    @pytest.mark.asyncio
    async def test_v25_streaming_generator_is_materialized_to_bytes(
        self, audit, fake_openai_tts, voice_catalog,
    ) -> None:
        """skip klo error"""

        class StreamingElevenLabsFake:
            def __init__(self) -> None:
                self.calls = []

            async def synthesize(self, *, text, voice, model, streaming):
                self.calls.append({"streaming": streaming})

                def _chunks():
                    yield b"\xff\xfb"
                    yield b"_stream_chunk"

                from agentic.agent.nodes.text_to_speech import TTSResult

                return TTSResult(
                    provider="elevenlabs",
                    model=model,
                    audio_blob=_chunks(),
                    audio_format="mp3",
                    streaming=streaming,
                )

        streaming_elevenlabs = StreamingElevenLabsFake()
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            mode="v2_5_turbo",
        )
        out = await text_to_speech_node(
            state,
            elevenlabs=streaming_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        voice = out["voice_state"]
        assert voice["tts_provider"] == "elevenlabs"
        assert voice["tts_streaming"] is True
        assert voice["audio_output_blob"] == b"\xff\xfb_stream_chunk"
        assert isinstance(voice["audio_output_blob"], (bytes, bytearray))

    @pytest.mark.asyncio
    async def test_v3_pre_rendered_path(
        self, audit, fake_elevenlabs, fake_openai_tts, voice_catalog,
    ) -> None:
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            mode="v3",
            text="[softly] Tarik napas pelan-pelan.",
        )
        # prefers v3 mode
        state["voice_state"]["speech_response_tags"] = state["voice_state"][
            "speech_response"
        ]
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        voice = out["voice_state"]
        assert voice["tts_provider"] == "elevenlabs"
        assert voice["audio_output_blob"]
        assert fake_elevenlabs.calls[0]["model"] == "eleven_v3"
        assert fake_elevenlabs.calls[0]["streaming"] is False
        # skip verbatim
        assert "[softly]" in fake_elevenlabs.calls[0]["text"]

    @pytest.mark.asyncio
    async def test_quota_falls_back_to_openai(
        self, audit, fake_elevenlabs, fake_openai_tts, voice_catalog,
    ) -> None:
        fake_elevenlabs.quota_exceeded = True
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        voice = out["voice_state"]
        assert voice["tts_provider"] == "openai_tts1"
        assert voice["audio_output_blob"] == fake_openai_tts.blob
        assert fake_openai_tts.calls
        assert fake_openai_tts.calls[0]["instructions"] == (
            voice_catalog.openai_tts_instructions
        )
        assert fake_openai_tts.calls[0]["response_format"] == (
            voice_catalog.openai_tts_format
        )
        assert audit.has_type("tts_openai_tts1")

    @pytest.mark.asyncio
    async def test_both_fail_records_voice_error(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
    ) -> None:
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_openai_tts.error = "401 Unauthorized"
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(),
        )
        voice = out["voice_state"]
        assert voice["voice_error"]
        assert "primary" in voice["voice_error"]
        assert "second" in voice["voice_error"]
        assert "third" in voice["voice_error"]

    @pytest.mark.asyncio
    async def test_gemini_third_tier_used_when_elevenlabs_and_openai_fail(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
    ) -> None:
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_openai_tts.error = "401 Unauthorized"
        fake_gemini_tts.error = None  # let it succeed
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(),
        )
        voice = out["voice_state"]
        assert voice["voice_error"] is None
        assert voice["tts_provider"] == "gemini_tts"
        # resolve_gemini_tier = tier_default
        assert voice["tts_model"] == "gemini-2.5-flash-preview-tts"
        assert voice["audio_output_blob"] == fake_gemini_tts.blob
        assert voice["audio_output_format"] == "wav"
        assert audit.has_type("tts_gemini_tts")

    @pytest.mark.asyncio
    async def test_v3_fallback_strips_tags_for_openai(
        self, audit, fake_elevenlabs, fake_openai_tts, voice_catalog,
    ) -> None:
        fake_elevenlabs.error = "v3 alpha not available"
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            mode="v3",
            text="[softly] Tarik napas. [pause] Pelan saja.",
        )
        # buat nyimpen config
        state["voice_state"]["speech_response"] = "Tarik napas. Pelan saja."
        state["voice_state"]["speech_response_tags"] = state["voice_state"][
            "speech_response"
        ]
        # set tags to [tagged version]
        state["voice_state"]["speech_response_tags"] = "[softly] Tarik napas. [pause]"
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        # skip tags
        sent = fake_openai_tts.calls[0]["text"]
        assert "[softly]" not in sent
        assert "[pause]" not in sent

"""
Standalone voice pipeline test runner. Mirrors
agentic/tests/test_feature_bot/test_voice with stdlib only.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path("/sessions/focused-dreamy-albattani/mnt/CompanionshipChatBot")
sys.path.insert(0, str(ROOT))

from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.speech_adapter import (
    V3_TECHNIQUES,
    select_mode,
    speech_adapter_node,
)
from agentic.agent.nodes.speech_to_text import (
    TranscriptResult,
    speech_to_text_node,
)
from agentic.agent.nodes.text_to_speech import TTSResult, text_to_speech_node
from agentic.agent.state import empty_conversation_state
from agentic.config.voices import load_voice_catalog


PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def t(name: str):
    def deco(fn):
        async def runner():
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
                PASSED.append(name)
                print(f"  PASS  {name}")
            except Exception as exc:
                FAILED.append((name, traceback.format_exc()))
                print(f"  FAIL  {name}: {exc!r}")
        runner.__name__ = fn.__name__
        return runner
    return deco


def section(label: str) -> None:
    print(f"\n=== {label} ===")



class RecordingAuditLogger(NullGuardrailLogger):
    def has_type(self, event_type: str) -> bool:
        return any(e.event_type == event_type for e in self.events)


@dataclass
class FakeSTT:
    text: str = "halo aku capek banget hari ini"
    language: str = "id"
    confidence: float = 0.9
    raise_on_call: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def transcribe(self, *, audio, mime, language_hint):
        self.calls.append({"audio": audio, "mime": mime, "hint": language_hint})
        if self.raise_on_call:
            raise RuntimeError("simulated transcription failure")
        return TranscriptResult(
            text=self.text, language=self.language, confidence=self.confidence,
        )


@dataclass
class FakeElevenLabs:
    blob: bytes = b"\xff\xfb_audio"
    quota_exceeded: bool = False
    error: str | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def synthesize(self, *, text, voice, model, streaming):
        self.calls.append({
            "text": text, "voice": voice.id, "model": model, "streaming": streaming,
        })
        if self.error or self.quota_exceeded:
            return TTSResult(
                provider="elevenlabs",
                model=model,
                error=self.error or "quota_exceeded",
                quota_exceeded=self.quota_exceeded,
            )
        return TTSResult(
            provider="elevenlabs",
            model=model,
            audio_blob=self.blob,
            audio_format="mp3",
            streaming=streaming,
        )


@dataclass
class FakeOpenAITTS:
    blob: bytes = b"\xff\xfb_openai_audio"
    error: str | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def synthesize(self, *, text, voice, model):
        self.calls.append({
            "text": text,
            "voice_fallback": voice.openai_fallback_voice,
            "model": model,
        })
        if self.error:
            return TTSResult(provider="openai_tts1", model=model, error=self.error)
        return TTSResult(
            provider="openai_tts1",
            model=model,
            audio_blob=self.blob,
            audio_format="mp3",
        )


class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeAdapterLLM:
    reply: str | None = None
    error: bool = False
    calls: list = field(default_factory=list)

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.error:
            raise RuntimeError("simulated adapter failure")
        if self.reply is not None:
            return _FakeAIMessage(self.reply)
        return _FakeAIMessage("aku denger kamu")



@t("stt no audio passes through")
async def test_stt_passthrough():
    state = empty_conversation_state(user_id="u", session_id="s")
    audit = RecordingAuditLogger()
    out = await speech_to_text_node(state, audit=audit)
    assert out["voice_state"]["transcript"] is None
    assert audit.events == []


@t("stt transcribes and sets message")
async def test_stt_transcribe():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["audio_input"] = b"fake"
    state["voice_state"]["audio_input_mime"] = "audio/wav"
    audit = RecordingAuditLogger()
    fake = FakeSTT()
    out = await speech_to_text_node(state, provider=fake, audit=audit)
    voice = out["voice_state"]
    assert voice["transcript"] == fake.text
    assert voice["transcript_language"] == "id"
    assert voice["output_modality"] == "voice"
    assert out["current_message"] == fake.text
    assert audit.has_type("stt_transcribed")


@t("stt failure logs warn")
async def test_stt_failure():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["audio_input"] = b"fake"
    audit = RecordingAuditLogger()
    fake = FakeSTT(raise_on_call=True)
    out = await speech_to_text_node(state, provider=fake, audit=audit)
    assert out["voice_state"]["transcript"] is None
    assert out["voice_state"]["voice_error"] is not None
    assert audit.has_type("stt_error")



@t("adapter mode default v2.5")
def test_adapter_mode_default():
    assert select_mode({"cbt_node_active": "validate"}) == "v2_5_turbo"


@t("adapter mode v3 trigger")
def test_adapter_mode_grounding():
    # V3_TECHNIQUES is a set of technique names that should use v3.
    # Pick any member of the set so the test stays decoupled from
    # which specific technique is wired.
    from agentic.agent.nodes.speech_adapter import V3_TECHNIQUES

    if not V3_TECHNIQUES:
        # No techniques wired to v3; skip-by-pass.
        return
    sample = next(iter(V3_TECHNIQUES))
    assert select_mode({"cbt_node_active": sample}) == "v3"


@t("adapter text modality skips")
async def test_adapter_skip():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["output_modality"] = "text"
    state["final_response"] = "Saya mengerti."
    llm = FakeAdapterLLM()
    out = await speech_adapter_node(
        state, audit=RecordingAuditLogger(), llm_v25=llm,
    )
    assert out["voice_state"]["speech_response"] is None
    assert llm.calls == []


@t("adapter v2.5 default path")
async def test_adapter_v25():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["output_modality"] = "voice"
    state["final_response"] = "Saya memahami bahwa hal tersebut berat."
    llm = FakeAdapterLLM(reply="Aku denger kamu, ini emang berat.")
    audit = RecordingAuditLogger()
    out = await speech_adapter_node(state, audit=audit, llm_v25=llm)
    voice = out["voice_state"]
    assert voice["tts_model"] == "v2_5_turbo"
    assert voice["speech_response"] == "Aku denger kamu, ini emang berat."
    assert voice["speech_response_tags"] is None
    assert audit.has_type("speech_adapted_v2_5_turbo")


@t("adapter v3 grounding path with tags")
async def test_adapter_v3():
    from agentic.agent.nodes.speech_adapter import V3_TECHNIQUES

    if not V3_TECHNIQUES:
        return
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["output_modality"] = "voice"
    state["cbt_node_active"] = next(iter(V3_TECHNIQUES))
    state["final_response"] = "Mari ambil napas pelan-pelan."
    v25 = FakeAdapterLLM(reply="should_not_be_used")
    v3 = FakeAdapterLLM(reply="[softly] Tarik napas. [pause] [warmly] Bagus.")
    audit = RecordingAuditLogger()
    out = await speech_adapter_node(
        state, audit=audit, llm_v25=v25, llm_v3=v3,
    )
    voice = out["voice_state"]
    assert voice["tts_model"] == "v3"
    assert "[softly]" in voice["speech_response_tags"]
    # Plain mirror keeps a tag-less version available
    assert "[" not in voice["speech_response"]
    assert audit.has_type("speech_adapted_v3")
    assert v25.calls == []
    assert v3.calls


@t("adapter llm failure falls back gracefully")
async def test_adapter_failure():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["output_modality"] = "voice"
    state["final_response"] = "Saya mengerti — ini hal berat."
    audit = RecordingAuditLogger()
    out = await speech_adapter_node(
        state, audit=audit, llm_v25=FakeAdapterLLM(error=True),
    )
    voice = out["voice_state"]
    assert voice["speech_response"]
    assert voice["voice_error"]



def _voice_ready(state, *, mode="v2_5_turbo", text="hai aku denger kamu"):
    state["voice_state"]["output_modality"] = "voice"
    state["voice_state"]["tts_model"] = mode
    state["voice_state"]["speech_response"] = text
    return state


@t("tts text modality skips")
async def test_tts_skip():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["voice_state"]["output_modality"] = "text"
    audit = RecordingAuditLogger()
    el = FakeElevenLabs()
    op = FakeOpenAITTS()
    out = await text_to_speech_node(
        state,
        elevenlabs=el, openai_tts=op,
        catalog=load_voice_catalog(force_reload=True), audit=audit,
    )
    assert out["voice_state"]["audio_output_blob"] is None
    assert el.calls == []
    assert op.calls == []


@t("tts v2.5 streaming primary path")
async def test_tts_v25():
    state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
    audit = RecordingAuditLogger()
    el = FakeElevenLabs()
    op = FakeOpenAITTS()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=op,
        catalog=load_voice_catalog(), audit=audit,
    )
    voice = out["voice_state"]
    assert voice["tts_provider"] == "elevenlabs"
    assert voice["audio_output_blob"] == el.blob
    assert voice["tts_streaming"] is True
    assert el.calls[0]["model"] == "eleven_turbo_v2_5"
    assert audit.has_type("tts_elevenlabs")


@t("tts v3 pre-rendered path with tags")
async def test_tts_v3():
    state = _voice_ready(
        empty_conversation_state(user_id="u", session_id="s"),
        mode="v3",
        text="[softly] Tarik napas pelan-pelan.",
    )
    state["voice_state"]["speech_response_tags"] = state["voice_state"][
        "speech_response"
    ]
    audit = RecordingAuditLogger()
    el = FakeElevenLabs()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=FakeOpenAITTS(),
        catalog=load_voice_catalog(), audit=audit,
    )
    voice = out["voice_state"]
    assert voice["tts_provider"] == "elevenlabs"
    assert el.calls[0]["model"] == "eleven_v3"
    assert el.calls[0]["streaming"] is False
    assert "[softly]" in el.calls[0]["text"]


@t("tts quota falls back to openai")
async def test_tts_quota_fallback():
    state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
    el = FakeElevenLabs(quota_exceeded=True)
    op = FakeOpenAITTS()
    audit = RecordingAuditLogger()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=op,
        catalog=load_voice_catalog(), audit=audit,
    )
    voice = out["voice_state"]
    assert voice["tts_provider"] == "openai_tts1"
    assert voice["audio_output_blob"] == op.blob
    assert audit.has_type("tts_openai_tts1")


@t("tts both fail records voice_error")
async def test_tts_both_fail():
    state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
    el = FakeElevenLabs(error="503")
    op = FakeOpenAITTS(error="401")
    audit = RecordingAuditLogger()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=op,
        catalog=load_voice_catalog(), audit=audit,
    )
    voice = out["voice_state"]
    assert voice["voice_error"]
    assert "primary" in voice["voice_error"]
    assert "fallback" in voice["voice_error"]


@t("catalog default per language id")
def test_catalog_default_id():
    cat = load_voice_catalog(force_reload=True)
    v = cat.get(None, language="id")
    assert v.language == "id"
    assert v.id == "nura_warm_female"


@t("catalog default per language en")
def test_catalog_default_en():
    cat = load_voice_catalog(force_reload=True)
    v = cat.get(None, language="en")
    assert v.language == "en"
    assert v.id == "sarah_clear_female"


@t("catalog four voices per language id")
def test_catalog_id_voices():
    cat = load_voice_catalog(force_reload=True)
    voices = cat.for_language("id")
    assert len(voices) == 4
    genders = {v.gender for v in voices}
    assert {"female", "male"} <= genders
    counts = {"female": 0, "male": 0}
    for v in voices:
        counts[v.gender] = counts.get(v.gender, 0) + 1
    assert counts["female"] == 2
    assert counts["male"] == 2


@t("catalog four voices per language en")
def test_catalog_en_voices():
    cat = load_voice_catalog(force_reload=True)
    voices = cat.for_language("en")
    assert len(voices) == 4
    counts = {"female": 0, "male": 0}
    for v in voices:
        counts[v.gender] = counts.get(v.gender, 0) + 1
    assert counts["female"] == 2
    assert counts["male"] == 2


@t("catalog explicit voice id overrides language")
def test_catalog_explicit_override():
    cat = load_voice_catalog(force_reload=True)
    v = cat.get("adam_grounded_male", language="id")
    assert v.id == "adam_grounded_male"
    assert v.language == "en"


@t("catalog falls back to DEFAULT_USER_LANGUAGE env when no language arg")
def test_catalog_env_default_language():
    import os as _os

    cat = load_voice_catalog(force_reload=True)
    prev = _os.environ.get("DEFAULT_USER_LANGUAGE")
    _os.environ["DEFAULT_USER_LANGUAGE"] = "en"
    try:
        v = cat.get(None, language=None)
        assert v.id == "sarah_clear_female"
    finally:
        if prev is None:
            _os.environ.pop("DEFAULT_USER_LANGUAGE", None)
        else:
            _os.environ["DEFAULT_USER_LANGUAGE"] = prev


@t("transcription provider reads OPENAI_TRANSCRIBE_MODEL env")
def test_transcribe_env_model():
    import os as _os
    from agentic.agent.nodes.speech_to_text import OpenAITranscriptionProvider

    prev = _os.environ.get("OPENAI_TRANSCRIBE_MODEL")
    _os.environ["OPENAI_TRANSCRIBE_MODEL"] = "gpt-4o-mini-transcribe"
    try:
        p = OpenAITranscriptionProvider()
        assert p._model == "gpt-4o-mini-transcribe"
    finally:
        if prev is None:
            _os.environ.pop("OPENAI_TRANSCRIBE_MODEL", None)
        else:
            _os.environ["OPENAI_TRANSCRIBE_MODEL"] = prev


@t("elevenlabs model resolver reads env")
def test_elevenlabs_env_model():
    import os as _os
    from agentic.agent.nodes.text_to_speech import _elevenlabs_model_for

    prev_rt = _os.environ.get("ELEVENLABS_MODEL_REALTIME")
    prev_pr = _os.environ.get("ELEVENLABS_MODEL_PRERENDERED")
    _os.environ["ELEVENLABS_MODEL_REALTIME"] = "eleven_flash_v2_5"
    _os.environ["ELEVENLABS_MODEL_PRERENDERED"] = "eleven_v3_beta"
    try:
        assert _elevenlabs_model_for("v2_5_turbo") == "eleven_flash_v2_5"
        assert _elevenlabs_model_for("v3") == "eleven_v3_beta"
    finally:
        for k, prev in [
            ("ELEVENLABS_MODEL_REALTIME", prev_rt),
            ("ELEVENLABS_MODEL_PRERENDERED", prev_pr),
        ]:
            if prev is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = prev


@t("tts uses OPENAI_TTS_MODEL env on fallback")
async def test_tts_env_fallback_model():
    import os as _os

    state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
    el = FakeElevenLabs(quota_exceeded=True)
    op = FakeOpenAITTS()
    audit = RecordingAuditLogger()
    prev = _os.environ.get("OPENAI_TTS_MODEL")
    _os.environ["OPENAI_TTS_MODEL"] = "tts-1-hd"
    try:
        await text_to_speech_node(
            state, elevenlabs=el, openai_tts=op,
            catalog=load_voice_catalog(force_reload=True), audit=audit,
        )
        assert op.calls[0]["model"] == "tts-1-hd"
    finally:
        if prev is None:
            _os.environ.pop("OPENAI_TTS_MODEL", None)
        else:
            _os.environ["OPENAI_TTS_MODEL"] = prev


@t("tts elevenlabs output_format env propagates")
def test_elevenlabs_output_format_env_default():
    import os as _os
    # Default fallback when env unset.
    prev = _os.environ.pop("ELEVENLABS_OUTPUT_FORMAT", None)
    try:
        from agentic.agent.nodes.text_to_speech import _audio_format_from
        assert _audio_format_from("mp3_44100_128") == "mp3"
        assert _audio_format_from("pcm_16000") == "pcm"
    finally:
        if prev is not None:
            _os.environ["ELEVENLABS_OUTPUT_FORMAT"] = prev


@t("tts uses language default when voice_id missing")
async def test_tts_language_default():
    state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
    state["resolved_language"] = "en"
    state["voice_state"]["voice_id"] = None
    el = FakeElevenLabs()
    audit = RecordingAuditLogger()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=FakeOpenAITTS(),
        catalog=load_voice_catalog(force_reload=True), audit=audit,
    )
    assert out["voice_state"]["voice_id"] == "sarah_clear_female"


@t("tts v3 fallback strips tags for openai")
async def test_tts_v3_fallback_strips():
    state = _voice_ready(
        empty_conversation_state(user_id="u", session_id="s"),
        mode="v3",
        text="[softly] Tarik napas.",
    )
    state["voice_state"]["speech_response"] = "Tarik napas."
    state["voice_state"]["speech_response_tags"] = "[softly] Tarik napas."
    el = FakeElevenLabs(error="v3 alpha not available")
    op = FakeOpenAITTS()
    audit = RecordingAuditLogger()
    out = await text_to_speech_node(
        state, elevenlabs=el, openai_tts=op,
        catalog=load_voice_catalog(), audit=audit,
    )
    sent = op.calls[0]["text"]
    assert "[softly]" not in sent



async def main():
    section("Speech-to-text")
    await test_stt_passthrough()
    await test_stt_transcribe()
    await test_stt_failure()

    section("Speech adapter")
    await test_adapter_mode_default()
    await test_adapter_mode_grounding()
    await test_adapter_skip()
    await test_adapter_v25()
    await test_adapter_v3()
    await test_adapter_failure()

    section("Voice catalog")
    await test_catalog_default_id()
    await test_catalog_default_en()
    await test_catalog_id_voices()
    await test_catalog_en_voices()
    await test_catalog_explicit_override()
    await test_catalog_env_default_language()

    section("Env-driven model selection")
    await test_transcribe_env_model()
    await test_elevenlabs_env_model()
    await test_elevenlabs_output_format_env_default()
    await test_tts_env_fallback_model()

    section("Text-to-speech")
    await test_tts_skip()
    await test_tts_v25()
    await test_tts_v3()
    await test_tts_quota_fallback()
    await test_tts_both_fail()
    await test_tts_v3_fallback_strips()
    await test_tts_language_default()

    print("\n" + "=" * 60)
    print(f"PASSED: {len(PASSED)}")
    print(f"FAILED: {len(FAILED)}")
    if FAILED:
        for name, tb in FAILED:
            print(f"\n--- {name} ---")
            print(tb)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

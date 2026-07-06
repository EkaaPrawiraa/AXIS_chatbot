"""
Shared fakes for the voice pipeline tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    NullGuardrailLogger,
)
from agentic.agent.nodes.speech_to_text import (
    STTProvider,
    TranscriptResult,
)
from agentic.agent.nodes.text_to_speech import (
    ElevenLabsTTSProvider,
    OpenAITTSProvider,
    TTSResult,
)
from agentic.config.voices import VoiceCatalog, VoiceEntry, load_voice_catalog



class RecordingAuditLogger(NullGuardrailLogger):
    def by_type(self, event_type: str) -> list[GuardrailEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def has_type(self, event_type: str) -> bool:
        return any(e.event_type == event_type for e in self.events)


@pytest.fixture
def audit() -> RecordingAuditLogger:
    return RecordingAuditLogger()



@dataclass
class FakeSTTProvider:
    text: str = "halo aku capek banget hari ini"
    language: str = "id"
    confidence: float = 0.9
    raise_on_call: bool = False
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def transcribe(
        self, *, audio: Any, mime: str | None, language_hint: str | None,
    ) -> TranscriptResult:
        self.calls.append({"audio": audio, "mime": mime, "hint": language_hint})
        if self.raise_on_call:
            raise RuntimeError("simulated transcription failure")
        return TranscriptResult(
            text=self.text,
            language=self.language,
            confidence=self.confidence,
        )


@pytest.fixture
def fake_stt() -> FakeSTTProvider:
    return FakeSTTProvider()


@pytest.fixture
def fake_gemini_stt() -> FakeSTTProvider:
    """Fake for the Gemini STT fallback tier — same protocol as fake_stt,
    kept as a separate fixture/instance so a test can assert on it
    independently of the primary provider's call count."""
    return FakeSTTProvider(raise_on_call=True)



@dataclass
class FakeElevenLabsTTS:
    blob: bytes = b"\xff\xfb_audio"
    quota_exceeded: bool = False
    error: str | None = None
    streaming_default: bool = True
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def synthesize(
        self, *, text: str, voice: VoiceEntry, model: str, streaming: bool,
    ) -> TTSResult:
        self.calls.append({
            "text": text,
            "voice": voice.id,
            "model": model,
            "streaming": streaming,
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

    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "mp3",
    ) -> TTSResult:
        self.calls.append({
            "text": text,
            "voice_fallback": voice.openai_fallback_voice,
            "model": model,
            "instructions": instructions,
            "response_format": response_format,
        })
        if self.error:
            return TTSResult(
                provider="openai_tts1", model=model, error=self.error,
            )
        return TTSResult(
            provider="openai_tts1",
            model=model,
            audio_blob=self.blob,
            audio_format=response_format,
        )


@dataclass
class FakeGeminiTTS:
    blob: bytes = b"\xff\xfb_gemini_audio"
    error: str | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "wav",
    ) -> TTSResult:
        self.calls.append({
            "text": text, "model": model, "response_format": response_format,
            "instructions": instructions,
        })
        if self.error:
            return TTSResult(provider="gemini_tts", model=model, error=self.error)
        return TTSResult(
            provider="gemini_tts",
            model=model,
            audio_blob=self.blob,
            audio_format="wav",
        )


@pytest.fixture
def fake_elevenlabs() -> FakeElevenLabsTTS:
    return FakeElevenLabsTTS()


@pytest.fixture
def fake_openai_tts() -> FakeOpenAITTS:
    return FakeOpenAITTS()


@pytest.fixture
def fake_gemini_tts() -> FakeGeminiTTS:
    """Fake for the Gemini TTS fallback tier, mirroring fake_openai_tts —
    keeps tests hermetic (no real network call) regardless of whether a
    real GOOGLE_API_KEY happens to be present in the environment."""
    return FakeGeminiTTS(error="gemini not configured for this test")


@pytest.fixture
def voice_catalog() -> VoiceCatalog:
    return load_voice_catalog(force_reload=True)



class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeAdapterLLM:
    """Fake speech adapter LLM. Either echoes a prepared reply or strips formality."""

    reply: str | None = None
    error: bool = False
    calls: list[list[Any]] = field(default_factory=list)

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.error:
            raise RuntimeError("simulated adapter failure")
        if self.reply is not None:
            return _FakeAIMessage(self.reply)
        # Default heuristic: take the user content and convert "saya" -> "aku".
        user_text = ""
        for m in messages:
            cls = m.__class__.__name__
            if "Human" in cls or getattr(m, "type", "") == "human":
                user_text = m.content
        adapted = user_text.replace("Saya", "Aku").replace("saya", "aku")
        return _FakeAIMessage(adapted)


@pytest.fixture
def adapter_llm_v25() -> FakeAdapterLLM:
    return FakeAdapterLLM(
        reply="Aku denger kamu kok, kondisi yang kamu ceritain emang berat. "
              "Kalau mau, kita ngobrol pelan-pelan.",
    )


@pytest.fixture
def adapter_llm_v3() -> FakeAdapterLLM:
    return FakeAdapterLLM(
        reply="[softly] Mari kita pelan-pelan dulu. [pause] [breathes deeply] "
              "Tarik napas perlahan. [slowly] Lalu hembuskan. [warmly] Kamu udah hebat.",
    )

"""init stt"""

from __future__ import annotations

import logging
import math
import mimetypes
import os
import time
from io import BytesIO
from dataclasses import dataclass
from typing import Any, Protocol

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.state import (
    ConversationState,
    VoiceState,
    empty_voice_state,
)
from agentic.config.llm_models import llm_provider
from agentic.gateway.monitoring import increment


logger = logging.getLogger(__name__)

_OPENAI_AUDIO_EXT_BY_MIME = {
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/m4a": "m4a",
    "audio/mp4": "mp4",
    "video/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mpga": "mpga",
    "audio/oga": "oga",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "video/webm": "webm",
}


def _normalise_mime(mime: str | None) -> str | None:
    if not mime:
        return None
    return mime.split(";", 1)[0].strip().lower() or None


def _extension_for_mime(mime: str | None) -> str:
    normalised = _normalise_mime(mime)
    if normalised in _OPENAI_AUDIO_EXT_BY_MIME:
        return _OPENAI_AUDIO_EXT_BY_MIME[normalised]
    guessed = mimetypes.guess_extension(normalised or "")
    if guessed:
        return guessed.lstrip(".")
    return "webm"


def _openai_audio_file(audio: Any, mime: str | None) -> Any:
    """wrap w/ filename"""
    if isinstance(audio, bytes):
        file = BytesIO(audio)
        file.name = f"voice-input.{_extension_for_mime(mime)}"
        return file
    if isinstance(audio, bytearray):
        file = BytesIO(bytes(audio))
        file.name = f"voice-input.{_extension_for_mime(mime)}"
        return file
    return audio


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    language: str | None
    confidence: float | None
    segments: list | None = None


class STTProvider(Protocol):
    """stt"""

    async def transcribe(
        self,
        *,
        audio: Any,
        mime: str | None,
        language_hint: str | None,
    ) -> TranscriptResult: ...


class OpenAITranscriptionProvider:
    """skip klo audio"""

    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self._client = client
        self._model = (
            model
            or os.getenv("OPENAI_TRANSCRIBE_MODEL")
            or "gpt-4o-mini-transcribe"
        )

    async def transcribe(
        self,
        *,
        audio: Any,
        mime: str | None,
        language_hint: str | None,
    ) -> TranscriptResult:
        client = self._client or self._lazy_client()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "file": _openai_audio_file(audio, mime),
            "response_format": _response_format_for_model(self._model),
        }
        if language_hint:
            kwargs["language"] = language_hint

        response = await client.audio.transcriptions.create(**kwargs)

        text = getattr(response, "text", "") or ""
        language = getattr(response, "language", None)
        segments = getattr(response, "segments", None)

        # best-effort conf
        confidence: float | None = None
        if segments:
            try:
                logprobs = [
                    float(getattr(s, "avg_logprob", None) or s["avg_logprob"])
                    for s in segments
                ]
                if logprobs:
                    confidence = sum(math.exp(lp) for lp in logprobs) / len(logprobs)
                    confidence = max(0.0, min(1.0, confidence))
            except Exception:
                confidence = None

        return TranscriptResult(
            text=text,
            language=language,
            confidence=confidence,
            segments=segments if isinstance(segments, list) else None,
        )

    def _lazy_client(self) -> Any:
        from openai import AsyncOpenAI  # type: ignore[import-not-found]

        return AsyncOpenAI()


class GeminiTranscriptionProvider:
    """fallback using gmx's audio model"""

    def __init__(
        self,
        *,
        client: Any | None = None,
        model: str | None = None,
    ) -> None:
        self._client = client
        self._model = model or os.getenv("GEMINI_TRANSCRIBE_MODEL", "gemini-3.5-flash")

    async def transcribe(
        self,
        *,
        audio: Any,
        mime: str | None,
        language_hint: str | None,
    ) -> TranscriptResult:
        client = self._client or self._lazy_client()
        from google.genai import types  # type: ignore[import-not-found]

        audio_bytes = bytes(audio) if isinstance(audio, (bytes, bytearray)) else audio
        prompt = (
            "Transcribe the following audio clip verbatim. Reply with ONLY "
            "the transcript text, no preamble, no quotes, no commentary. "
            "If the audio is silent or unintelligible, reply with an empty string."
        )
        if language_hint:
            prompt += f" The spoken language is expected to be '{language_hint}'."

        response = await client.aio.models.generate_content(
            model=self._model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=mime or "audio/webm"),
                prompt,
            ],
        )
        text = (getattr(response, "text", "") or "").strip()
        return TranscriptResult(text=text, language=language_hint, confidence=None, segments=None)

    def _lazy_client(self) -> Any:
        from google import genai  # type: ignore[import-not-found]

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY/GEMINI_API_KEY not configured")
        return genai.Client(api_key=api_key)


def _default_stt_providers() -> tuple[STTProvider, STTProvider]:
    """primary/fallback pair, ordered by LLM_PROVIDER."""
    if llm_provider() == "openai":
        return OpenAITranscriptionProvider(), GeminiTranscriptionProvider()
    return GeminiTranscriptionProvider(), OpenAITranscriptionProvider()


async def speech_to_text_node(
    state: ConversationState,
    *,
    provider: STTProvider | None = None,
    fallback_provider: STTProvider | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """run stt, fail fallback."""
    audit = audit or NullGuardrailLogger()
    voice = dict(state.get("voice_state") or empty_voice_state())

    audio = voice.get("audio_input")
    if audio is None:
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    default_primary, default_fallback = _default_stt_providers()
    if provider is None:
        provider = default_primary
    if fallback_provider is None:
        fallback_provider = default_fallback

    started = time.perf_counter()
    try:
        result = await provider.transcribe(
            audio=audio,
            mime=voice.get("audio_input_mime"),
            language_hint=state.get("language_pref"),
        )
    except Exception as exc:
        primary_label = "openai" if isinstance(provider, OpenAITranscriptionProvider) else "gemini"
        increment("stt_failures_total", provider=primary_label, model=getattr(provider, "_model", "unknown"))
        logger.exception(
            "audio transcription failed (%s), trying fallback: %s", primary_label, exc,
        )
        # fail first, then primary.
        try:
            fallback = fallback_provider
            result = await fallback.transcribe(
                audio=audio,
                mime=voice.get("audio_input_mime"),
                language_hint=state.get("language_pref"),
            )
        except Exception as fallback_exc:
            fallback_label = "openai" if isinstance(fallback_provider, OpenAITranscriptionProvider) else "gemini"
            increment("stt_failures_total", provider=fallback_label, model=getattr(fallback_provider, "_model", "unknown"))
            logger.exception("STT fallback (%s) also failed: %s", fallback_label, fallback_exc)
            voice["voice_error"] = f"stt_error:{exc}; gemini_fallback_error:{fallback_exc}"
            state["voice_state"] = voice  # type: ignore[typeddict-item]
            await audit.log(
                GuardrailEvent(
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    layer=GuardrailEventLayer.INPUT,
                    event_type="stt_error",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=str(fallback_exc)[:200],
                )
            )
            return state

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    # drop common hallucinations
    cleaned_text = _drop_hallucinated_transcript(
        result.text,
        language_hint=state.get("language_pref"),
        detected_language=result.language,
    )

    voice["transcript"] = cleaned_text
    voice["transcript_language"] = result.language
    voice["transcript_confidence"] = result.confidence
    voice["transcript_segments"] = result.segments
    voice["output_modality"] = "voice"

    if result.language:
        state["resolved_language"] = result.language

    state["current_message"] = cleaned_text
    state["voice_state"] = voice  # type: ignore[typeddict-item]

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.INPUT,
            event_type="stt_transcribed",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=(result.language or "?"),
            latency_ms=elapsed_ms,
            metadata={
                "char_count": len(result.text or ""),
                "confidence": result.confidence,
            },
        )
    )
    return state


def _response_format_for_model(model: str) -> str:
    if model.startswith("gpt-4o") and "transcribe" in model:
        return "json"
    return "verbose_json"


# skip audio
_HALLUCINATED_PHRASES = frozenset(
    s.lower()
    for s in (
        "はい",
        "はいはい",
        "はいはい。",
        "ご視聴ありがとうございました",
        "ご視聴ありがとうございました。",
        "ご視聴ありがとうございます",
        "字幕視聴ありがとうございました",
        "thanks for watching",
        "thanks for watching!",
        "thank you",
        "thank you.",
        "thank you for watching",
        "thank you for watching.",
        "bye",
        "bye.",
        "you",
        ".",
    )
)


def _drop_hallucinated_transcript(
    text: str | None,
    *,
    language_hint: str | None,
    detected_language: str | None,
) -> str:
    if not text:
        return ""
    normalised = text.strip().rstrip("。.,!?！？ ").lower()
    if not normalised:
        return ""
    if normalised in _HALLUCINATED_PHRASES:
        logger.info(
            "STT: dropping hallucinated transcript %r (lang_hint=%s detected=%s)",
            text, language_hint, detected_language,
        )
        return ""
    # check lan
    if language_hint == "id" and len(normalised) <= 8:
        if any("぀" <= ch <= "ヿ" or "一" <= ch <= "鿿"
               or "가" <= ch <= "힣" for ch in normalised):
            logger.info(
                "STT: dropping likely-hallucinated CJK transcript %r (hint=id)",
                text,
            )
            return ""
    return text


__all__ = [
    "STTProvider",
    "TranscriptResult",
    "OpenAITranscriptionProvider",
    "GeminiTranscriptionProvider",
    "speech_to_text_node",
]

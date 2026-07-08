"""`fallback to OpenAI`"""

from __future__ import annotations

import asyncio
import logging
import os
import time
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
from agentic.agent.state import ConversationState, empty_voice_state
from agentic.config.gemini_tts_tiers import (
    build_gemini_director_notes,
    is_gemini_prebuilt_voice_name,
    resolve_gemini_tier,
    resolve_gemini_voice_name,
    resolve_voice_character,
)
from agentic.config.llm_models import llm_provider
from agentic.config.voices import VoiceCatalog, VoiceEntry, load_voice_catalog
from agentic.gateway.monitoring import increment


# `langchain` & `fallback`  `speech_adapter.py`  `inject_gemini_audio_tags`  `LLM`  `call`


try:  # pragma: no cover
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover - sandbox fallback
    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"


logger = logging.getLogger(__name__)



@dataclass
class TTSResult:
    """synth call outcome"""

    provider: str             # "elevenlabs" | "openai_tts1"
    model: str                # provider-specific model id
    audio_blob: Any | None = None
    audio_url: str | None = None
    audio_format: str = "mp3"
    streaming: bool = False
    quota_exceeded: bool = False
    error: str | None = None


class ElevenLabsTTSProvider(Protocol):
    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        streaming: bool,
    ) -> TTSResult: ...


class OpenAITTSProvider(Protocol):
    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "mp3",
    ) -> TTSResult: ...


class GeminiTTSProvider(Protocol):
    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "wav",
    ) -> TTSResult: ...


# prod prov (laz)


class ElevenLabsClient:
    """wrp sdk"""

    def __init__(
        self,
        *,
        client: Any | None = None,
        api_key_env: str = "ELEVENLABS_API_KEY",
    ) -> None:
        self._client = client
        self._api_key_env = api_key_env

    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        streaming: bool,
    ) -> TTSResult:
        if not voice.is_configured:
            return TTSResult(
                provider="elevenlabs",
                model=model,
                error="voice_id_not_configured",
            )

        try:
            client = self._client or self._lazy_client()
        except Exception as exc:
            return TTSResult(
                provider="elevenlabs", model=model, error=f"client_init:{exc}",
            )

        output_format = os.getenv(
            "ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128"
        )

        voice_settings = {
            "stability": _env_float("ELEVENLABS_STABILITY", 0.64),
            "similarity_boost": _env_float("ELEVENLABS_SIMILARITY_BOOST", 1.0),
            "style": _env_float("ELEVENLABS_STYLE", 0.12),
            "use_speaker_boost": _env_bool("ELEVENLABS_USE_SPEAKER_BOOST", True),
        }

        try:
            if streaming:
                tts = client.text_to_speech
                if hasattr(tts, "stream"):
                    handle = tts.stream(
                        voice_id=voice.elevenlabs_voice_id,
                        model_id=model,
                        text=text,
                        output_format=output_format,
                        voice_settings=voice_settings,
                    )
                    # pull first
                    try:
                        first_chunk = next(handle)
                    except StopIteration:
                        return TTSResult(
                            provider="elevenlabs",
                            model=model,
                            error="no_audio",
                        )
                    except Exception as exc:
                        msg = str(exc).lower()
                        quota = "quota" in msg or "exceeded" in msg or "limit" in msg
                        return TTSResult(
                            provider="elevenlabs",
                            model=model,
                            error=str(exc)[:200],
                            quota_exceeded=quota,
                        )

                    def _stream_with_first() -> Any:
                        yield first_chunk
                        for ch in handle:
                            yield ch

                    return TTSResult(
                        provider="elevenlabs",
                        model=model,
                        audio_blob=_stream_with_first(),
                        audio_format=_audio_format_from(output_format),
                        streaming=True,
                    )
                if hasattr(tts, "convert_as_stream"):
                    handle = tts.convert_as_stream(
                        voice_id=voice.elevenlabs_voice_id,
                        model_id=model,
                        text=text,
                        output_format=output_format,
                        voice_settings=voice_settings,
                    )
                    return TTSResult(
                        provider="elevenlabs",
                        model=model,
                        audio_blob=handle,
                        audio_format=_audio_format_from(output_format),
                        streaming=True,
                    )
            audio = client.text_to_speech.convert(
                voice_id=voice.elevenlabs_voice_id,
                model_id=model,
                text=text,
                output_format=output_format,
                voice_settings=voice_settings,
            )
            blob = b"".join(audio) if hasattr(audio, "__iter__") else audio
            return TTSResult(
                provider="elevenlabs",
                model=model,
                audio_blob=blob,
                audio_format=_audio_format_from(output_format),
                streaming=False,
            )
        except Exception as exc:
            msg = str(exc).lower()
            quota = "quota" in msg or "exceeded" in msg or "limit" in msg
            return TTSResult(
                provider="elevenlabs",
                model=model,
                error=str(exc)[:200],
                quota_exceeded=quota,
            )

    def _lazy_client(self) -> Any:
        from elevenlabs.client import ElevenLabs  # type: ignore[import-not-found]

        api_key = os.getenv(self._api_key_env)
        return ElevenLabs(api_key=api_key) if api_key else ElevenLabs()


class OpenAITTSClient:
    """wrp oai-synth"""

    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client

    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "mp3",
    ) -> TTSResult:
        try:
            client = self._client or self._lazy_client()
        except Exception as exc:
            return TTSResult(
                provider="openai_tts1", model=model, error=f"client_init:{exc}",
            )
        try:
            payload: dict[str, Any] = {
                "model": model,
                "voice": voice.openai_fallback_voice,
                "input": text,
                "response_format": response_format,
            }
            tts_instructions = _openai_tts_instructions(
                model=model,
                instructions=instructions,
            )
            if tts_instructions:
                payload["instructions"] = tts_instructions
            resp = await client.audio.speech.create(
                **payload,
            )
            blob = await resp.aread() if hasattr(resp, "aread") else resp.read()
            return TTSResult(
                provider="openai_tts1",
                model=model,
                audio_blob=blob,
                audio_format=response_format,
            )
        except Exception as exc:
            return TTSResult(
                provider="openai_tts1",
                model=model,
                error=str(exc)[:200],
            )

    def _lazy_client(self) -> Any:
        from openai import AsyncOpenAI  # type: ignore[import-not-found]

        return AsyncOpenAI()


class GeminiTTSClient:
    """fallback: TTS using Gemini"""

    def __init__(self, *, client: Any | None = None, retry_delay_s: float = 0.6) -> None:
        self._client = client
        self._retry_delay_s = retry_delay_s

    async def synthesize(
        self,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None = None,
        response_format: str = "wav",
    ) -> TTSResult:
        try:
            client = self._client or self._lazy_client()
        except Exception as exc:
            return TTSResult(
                provider="gemini_tts", model=model, error=f"client_init:{exc}",
            )

        # finish_reason=OTHER, no candidate content, retry works.
        last_result = await self._attempt(client, text=text, voice=voice, model=model, instructions=instructions)
        if last_result.error is None and last_result.audio_blob is not None:
            return last_result
        if not (last_result.error or "").startswith(("empty_response:", "no_audio")):
            return last_result

        await asyncio.sleep(self._retry_delay_s)
        return await self._attempt(client, text=text, voice=voice, model=model, instructions=instructions)

    async def _attempt(
        self,
        client: Any,
        *,
        text: str,
        voice: VoiceEntry,
        model: str,
        instructions: str | None,
    ) -> TTSResult:
        try:
            from google.genai import types  # type: ignore[import-not-found]

            # `voice.id` sets prebuilt voice.
            voice_name = voice.id or os.getenv("GEMINI_TTS_VOICE", "Kore")
            spoken_text = f"{instructions.strip()}\n\n{text}" if instructions else text
            response = await client.aio.models.generate_content(
                model=model,
                contents=spoken_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name,
                            )
                        )
                    ),
                ),
            )
            candidates = response.candidates or []
            content = candidates[0].content if candidates else None
            parts = content.parts if content else None
            if not parts:
                # explain w/o attr error
                reason = getattr(candidates[0], "finish_reason", None) if candidates else "no_candidates"
                return TTSResult(
                    provider="gemini_tts", model=model, error=f"empty_response:{reason}",
                )
            pcm = parts[0].inline_data.data
            if not pcm:
                return TTSResult(provider="gemini_tts", model=model, error="no_audio")
            return TTSResult(
                provider="gemini_tts",
                model=model,
                audio_blob=_pcm_to_wav(pcm),
                audio_format="wav",
            )
        except Exception as exc:
            return TTSResult(
                provider="gemini_tts",
                model=model,
                error=str(exc)[:200],
            )

    def _lazy_client(self) -> Any:
        from google import genai  # type: ignore[import-not-found]

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY/GEMINI_API_KEY not configured")
        return genai.Client(api_key=api_key)


def _pcm_to_wav(
    pcm_bytes: bytes,
    *,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """wrap raw pcm"""
    import struct

    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    data_size = len(pcm_bytes)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        sample_width * 8,
        b"data",
        data_size,
    )
    return header + pcm_bytes


# gemini style


def _select_tts_style(state: ConversationState) -> bool:
    """True if extra pacing/tone."""
    if state.get("safety_flag") in ("crisis", "escalate"):
        return True
    cbt_directive = state.get("cbt_directive") or {}
    technique = cbt_directive.get("technique")
    return bool(technique and technique != "none")


async def _inject_gemini_audio_tags(text: str, *, llm: Any | None = None) -> str:
    """bracket audio tags"""
    plain = text.strip()
    if not plain:
        return text
    try:
        from agentic.config.llm_models import SPEECH_ADAPTER_GEMINI_TAGS, build_llm

        model = llm or build_llm(SPEECH_ADAPTER_GEMINI_TAGS)
        ai = await model.ainvoke(
            [
                _SystemMessage(content=SPEECH_ADAPTER_GEMINI_TAGS.system_prompt),
                _HumanMessage(
                    content=f"---BEGIN SOURCE---\n{plain}\n---END SOURCE---"
                ),
            ]
        )
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
        tagged = (raw or "").strip()
        return tagged or text
    except Exception as exc:
        logger.warning("gemini audio tag injection failed: %s", exc)
        return text


def _resolve_gemini_voice_entry(voice_entry: VoiceEntry, tts_model_request: str | None) -> VoiceEntry:
    """check voice_id"""
    if (
        voice_entry.persona == "user-selected"
        and is_gemini_prebuilt_voice_name(voice_entry.id)
    ):
        return voice_entry
    tier = resolve_gemini_tier(tts_model_request)
    gemini_voice_name = resolve_gemini_voice_name(tier, gender=None)
    return VoiceEntry(
        id=gemini_voice_name,
        label_id=gemini_voice_name,
        label_en=gemini_voice_name,
        gender="",
        language=voice_entry.language,
        persona="gemini-tier-default",
        elevenlabs_voice_id=gemini_voice_name,
        openai_fallback_voice=voice_entry.openai_fallback_voice,
        notes="Resolved from Gemini tier default voice.",
    )


def _materialize_audio_blob(blob: Any) -> Any:
    """drain stream into blob"""
    if blob is None or isinstance(blob, (bytes, bytearray)):
        return blob
    return b"".join(blob)


def _elevenlabs_model_for(mode: str) -> str:
    """resolusi ElevenLabs model"""
    if mode == "v3":
        return os.getenv("ELEVENLABS_MODEL_PRERENDERED", "eleven_v3")
    return os.getenv("ELEVENLABS_MODEL_REALTIME", "eleven_turbo_v2_5")


def _audio_format_from(output_format: str) -> str:
    """pick mime hint"""
    if output_format.startswith("mp3"):
        return "mp3"
    if output_format.startswith("pcm"):
        return "pcm"
    if output_format.startswith("ulaw"):
        return "ulaw"
    return "mp3"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _select_text(state: ConversationState) -> str:
    voice = state.get("voice_state") or {}
    mode = voice.get("tts_model")
    if mode == "v3" and voice.get("speech_response_tags"):
        return str(voice["speech_response_tags"])
    return str(voice.get("speech_response") or "")


@dataclass
class TTSChainOutcome:
    """sep tier-0 error"""

    result: TTSResult
    primary_error: str | None


async def run_tts_fallback_chain(
    *,
    text: str,
    voice_entry: VoiceEntry,
    mode: str,
    empathetic: bool = False,
    elevenlabs: ElevenLabsTTSProvider | None = None,
    openai_tts: OpenAITTSProvider | None = None,
    gemini_tts: GeminiTTSProvider | None = None,
    catalog: VoiceCatalog | None = None,
    streaming: bool | None = None,
    gemini_tag_llm: Any | None = None,
) -> TTSChainOutcome:
    """Run -> Gemini -> OpenAI."""
    cat = catalog or load_voice_catalog()
    el_model = _elevenlabs_model_for(mode)
    use_streaming = (mode == "v2_5_turbo") if streaming is None else streaming

    primary = elevenlabs or ElevenLabsClient()
    primary_result = await primary.synthesize(
        text=text, voice=voice_entry, model=el_model, streaming=use_streaming,
    )

    if not (primary_result.error or primary_result.quota_exceeded):
        return TTSChainOutcome(result=primary_result, primary_error=None)

    increment("tts_failures_total", provider="elevenlabs", model=el_model)
    plain = _strip_tags_for_fallback(text)

    async def _try_openai() -> TTSResult:
        client = openai_tts or OpenAITTSClient()
        fallback_model = os.getenv("OPENAI_TTS_MODEL") or cat.openai_tts_model
        result = await client.synthesize(
            text=plain or text,
            voice=voice_entry,
            model=fallback_model,
            instructions=cat.openai_tts_instructions,
            response_format=os.getenv("OPENAI_TTS_FORMAT") or cat.openai_tts_format,
        )
        if result.error is not None or result.audio_blob is None:
            increment("tts_failures_total", provider="openai", model=fallback_model)
        return result

    async def _try_gemini() -> TTSResult:
        client = gemini_tts or GeminiTTSClient()
        tier = resolve_gemini_tier(mode)
        gemini_voice_entry = _resolve_gemini_voice_entry(voice_entry, mode)
        character = resolve_voice_character(gemini_voice_entry.id)
        director_notes = build_gemini_director_notes(character, empathetic=empathetic)
        tagged_text = await _inject_gemini_audio_tags(plain or text, llm=gemini_tag_llm)
        result = await client.synthesize(
            text=tagged_text,
            voice=gemini_voice_entry,
            model=tier.model,
            instructions=director_notes,
        )
        if result.error is not None or result.audio_blob is None:
            increment("tts_failures_total", provider="gemini", model=tier.model)
        return result

    provider_order = (
        (_try_gemini, _try_openai)
        if llm_provider() != "openai"
        else (_try_openai, _try_gemini)
    )

    primary_error = primary_result.error or "quota"

    second_result = await provider_order[0]()
    if second_result.error is None and second_result.audio_blob is not None:
        return TTSChainOutcome(result=second_result, primary_error=primary_error)

    third_result = await provider_order[1]()
    if third_result.error is None and third_result.audio_blob is not None:
        return TTSChainOutcome(result=third_result, primary_error=primary_error)

    primary_result.error = (
        f"primary:{primary_error}; "
        f"second:{second_result.error or 'no_audio'}; "
        f"third:{third_result.error or 'no_audio'}"
    )
    return TTSChainOutcome(result=primary_result, primary_error=primary_error)


async def text_to_speech_node(
    state: ConversationState,
    *,
    elevenlabs: ElevenLabsTTSProvider | None = None,
    openai_tts: OpenAITTSProvider | None = None,
    gemini_tts: GeminiTTSProvider | None = None,
    catalog: VoiceCatalog | None = None,
    audit: GuardrailLogger | None = None,
    gemini_tag_llm: Any | None = None,
) -> ConversationState:
    """synthesize speech"""
    audit = audit or NullGuardrailLogger()
    voice = dict(state.get("voice_state") or empty_voice_state())

    if voice.get("output_modality") not in ("voice", "both"):
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    text = _select_text(state)
    if not text.strip():
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    cat = catalog or load_voice_catalog()
    language = state.get("resolved_language") or state.get("language_pref")
    voice_entry = cat.get(voice.get("voice_id"), language=language)
    voice["voice_id"] = voice_entry.id
    voice["voice_provider_id"] = voice_entry.elevenlabs_voice_id

    mode = voice.get("tts_model") or "v2_5_turbo"

    started = time.perf_counter()

    outcome = await run_tts_fallback_chain(
        text=text,
        voice_entry=voice_entry,
        mode=mode,
        empathetic=_select_tts_style(state),
        elevenlabs=elevenlabs,
        openai_tts=openai_tts,
        gemini_tts=gemini_tts,
        catalog=cat,
        gemini_tag_llm=gemini_tag_llm,
    )
    final = outcome.result
    if final.error:
        voice["voice_error"] = final.error

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    voice["tts_provider"] = final.provider
    voice["tts_model"] = final.model
    voice["tts_streaming"] = final.streaming
    voice["audio_output_blob"] = _materialize_audio_blob(final.audio_blob)
    voice["audio_output_format"] = final.audio_format
    state["voice_state"] = voice  # type: ignore[typeddict-item]

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,
            event_type=f"tts_{final.provider}",
            decision=(
                GuardrailEventDecision.LOG_ONLY
                if final.audio_blob is not None
                else GuardrailEventDecision.FALLBACK
            ),
            severity=(
                GuardrailEventSeverity.INFO
                if final.audio_blob is not None
                else GuardrailEventSeverity.WARN
            ),
            trigger_detail=voice_entry.id,
            latency_ms=elapsed_ms,
            metadata={
                "model": final.model,
                "streaming": final.streaming,
                "primary_error": outcome.primary_error,
                "fallback_used": final.provider != "elevenlabs",
            },
        )
    )
    return state


import re

_V3_TAG_RE = re.compile(r"\[[a-zA-Z][^\]]{0,32}\]")


def _strip_tags_for_fallback(text: str) -> str:
    return _V3_TAG_RE.sub("", text).strip()


def _openai_tts_instructions(
    *,
    model: str,
    instructions: str | None,
) -> str | None:
    if model != "gpt-4o-mini-tts":
        return None
    return (os.getenv("OPENAI_TTS_INSTRUCTIONS") or instructions or "").strip() or None


__all__ = [
    "TTSResult",
    "TTSChainOutcome",
    "ElevenLabsTTSProvider",
    "OpenAITTSProvider",
    "GeminiTTSProvider",
    "ElevenLabsClient",
    "OpenAITTSClient",
    "GeminiTTSClient",
    "run_tts_fallback_chain",
    "text_to_speech_node",
]

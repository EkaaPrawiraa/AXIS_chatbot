"""init state"""

from __future__ import annotations

import base64
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic.agent.state import OutputModality, TTSModelChoice


class ChatMessage(BaseModel):
    """get last msg"""

    role: Literal["user", "assistant", "system"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VoiceTurnRequest(BaseModel):
    """VoiceInputs: VoiceState."""

    output_modality: OutputModality = "text"
    audio_input_base64: str | None = None
    audio_input_mime: str | None = None
    audio_input_url: str | None = None
    voice_id: str | None = None
    tts_model: TTSModelChoice | None = None
    tts_streaming: bool | None = None

    @model_validator(mode="after")
    def validate_audio_input(self) -> "VoiceTurnRequest":
        if self.audio_input_base64 and self.audio_input_url:
            raise ValueError(
                "Use only one of audio_input_base64 or audio_input_url per turn."
            )
        if self.audio_input_base64 and not self.audio_input_mime:
            raise ValueError("audio_input_mime is required with audio_input_base64.")
        return self

    def decoded_audio_input(self) -> bytes | str | None:
        """ret bytes audio, url/path, or None."""
        if self.audio_input_base64:
            return base64.b64decode(self.audio_input_base64)
        return self.audio_input_url


class ChatTurnRequest(BaseModel):
    """backend-authorized user to LangGraph"""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    session_id: str
    current_message: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    session_turn: int = 0

    language_pref: str | None = "id"
    preferred_response_model: str | None = None
    resolved_language: str | None = None
    linguistic_signals: dict[str, Any] | None = None

    safety_flag: str | None = None
    kg_context: str | None = None

    cbt_node_active: str | None = None
    cbt_directive: dict[str, Any] | None = None
    cbt_state: dict[str, Any] | None = None
    phq9_state: dict[str, Any] | None = None

    voice: VoiceTurnRequest = Field(default_factory=VoiceTurnRequest)
    include_state: bool = False
    confession_mode: bool = False
    single_pass_voice: bool = False

    @model_validator(mode="after")
    def validate_turn_input(self) -> "ChatTurnRequest":
        has_text = bool((self.current_message or "").strip())
        has_audio = bool(self.voice.audio_input_base64 or self.voice.audio_input_url)
        if not has_text and not has_audio:
            raise ValueError(
                "Either current_message or voice audio input is required."
            )
        return self


class VoiceTurnResponse(BaseModel):
    """ngambil grafik"""

    transcript: str | None = None
    transcript_confidence: float | None = None
    transcript_language: str | None = None
    output_modality: OutputModality | None = None
    voice_id: str | None = None
    voice_provider_id: str | None = None
    speech_response: str | None = None
    speech_response_tags: str | None = None
    # `str`, not `TTSModelChoice`: restrict to `which mode`.
    tts_model: str | None = None
    tts_provider: str | None = None
    tts_streaming: bool | None = None
    audio_output_base64: str | None = None
    audio_output_url: str | None = None
    audio_output_format: str | None = None
    voice_error: str | None = None


class SynthesizeSpeechRequest(BaseModel):
    """play msg outside chat turn"""

    text: str
    voice_id: str | None = None
    tts_model: TTSModelChoice | None = None
    language_pref: str | None = "id"


class SynthesizeSpeechResponse(BaseModel):
    """buat json respon"""

    audio_output_base64: str | None = None
    audio_output_url: str | None = None
    audio_output_format: str | None = None
    tts_provider: str | None = None
    voice_id: str | None = None
    voice_provider_id: str | None = None
    tts_model: str | None = None
    voice_error: str | None = None


class TranscribeSpeechRequest(BaseModel):
    """skip llm reply"""

    audio_base64: str
    audio_mime: str | None = None
    language_pref: str | None = "id"


class TranscribeSpeechResponse(BaseModel):
    """buat json"""

    text: str
    language: str | None = None
    confidence: float | None = None
    voice_error: str | None = None


class ChatTurnResponse(BaseModel):
    """res grafik."""

    user_id: str
    session_id: str
    reply: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    session_turn: int | None = None

    resolved_language: str | None = None
    linguistic_signals: dict[str, Any] | None = None
    safety_flag: str | None = None
    crisis_tier: str | None = None
    kg_context: str | None = None

    cbt_node_active: str | None = None
    cbt_directive: dict[str, Any] | None = None
    cbt_state: dict[str, Any] | None = None
    phq9_state: dict[str, Any] | None = None
    voice: VoiceTurnResponse = Field(default_factory=VoiceTurnResponse)

    state: dict[str, Any] | None = None

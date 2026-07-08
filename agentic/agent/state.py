"""init state"""

from __future__ import annotations

from typing import Any, List, Literal, Optional, TypedDict



OutputModality = Literal["text", "voice", "both"]
# legacy, preview, shorter, gemini_tts_tiers.
TTSModelChoice = Literal[
    "v2_5_turbo",
    "v3",
    "openai_tts1",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-pro-preview-tts",
    "gemini-2.5-flash-preview-tts",
    "gemini-3.1-flash-tts",
    "gemini-2.5-pro-tts",
    "gemini-2.5-flash-tts",
]


class VoiceState(TypedDict, total=False):
    """init state"""

    # input.
    audio_input: Optional[Any]            # bytes | path string | URL
    audio_input_mime: Optional[str]
    transcript: Optional[str]
    transcript_confidence: Optional[float]
    transcript_language: Optional[str]    # detected by STT
    transcript_segments: Optional[list]   # optional STT word/segment detail

    # ekstrak data
    output_modality: OutputModality
    voice_id: Optional[str]               # selected voice id (catalog key)
    voice_provider_id: Optional[str]      # provider-specific id (ElevenLabs)
    speech_response: Optional[str]        # adapter output (spoken-style text)
    speech_response_tags: Optional[str]   # v3 tagged version when applicable
    tts_model: Optional[TTSModelChoice]
    tts_provider: Optional[str]           # "elevenlabs" | "openai_tts1"
    tts_streaming: bool
    audio_output_url: Optional[str]
    audio_output_blob: Optional[Any]      # in-memory bytes for tests / fallback
    audio_output_format: Optional[str]    # "mp3" | "wav" | etc.
    voice_error: Optional[str]            # populated on fallback path
    speech_adapted_in_generator: bool     # True if LLM adapter skipped in single-pass

# init state


PHQ9Tier = Literal["scheduled", "event"]
PHQ9Phase = Literal[
    "idle",            # no offer pending
    "offer_pending",   # gate passed, waiting for warm-up turns
    "offered",         # offer message has been shown
    "declined",        # user declined this session
    "in_progress",     # actively asking items
    "awaiting_clar",   # awaiting clarification on current item
    "completed",       # all 9 items scored
    "deferred_crisis", # finished, item9 flagged, awaiting guardrail
]


# init state


class CBTState(TypedDict, total=False):
    """``ConversationState["cbt_state"]``"""

    last_offered: Optional[str]            # technique name from CBTTechnique
    declined_last_offer: bool
    decline_streak: int                    # consecutive declines for cooldown
    thought_record_active: bool
    thought_record: Optional[dict]         # ThoughtRecordSubState.to_dict()
    last_directive: Optional[dict]         # last CBTDecision payload (audit)


class PHQ9SessionState(TypedDict, total=False):
    """set by PHQ-9"""

    phase: PHQ9Phase
    tier: Optional[PHQ9Tier]
    reason: Optional[str]
    language: Optional[str]
    offer_made_at_turn: Optional[int]
    active_item: Optional[int]      # 1..9
    awaiting_clarification: bool
    responses: dict                  # {item_id: {score, source, raw_text, confidence}}
    last_total: Optional[int]
    last_severity: Optional[str]
    item9_flagged: bool
    route_to_crisis_after: bool
    retry_scheduled_at: Optional[str]   # ISO8601
    # skip
    back_count: int                  # number of times user asked to revise
    last_judge_action: Optional[str] # "advance" | "clarify" | "back" | "score_only"
    last_judge_rationale: Optional[str]
    # init state
    user_initiated: bool             # True when user explicitly requested PHQ-9
    offer_armed: bool                # True when response_generator should weave invite


class ProfileContext(TypedDict, total=False):
    """minimal profile"""

    display_name: Optional[str]
    preferred_language: Optional[str]



class ConversationState(TypedDict, total=False):
    """init state"""

    # ident dan dialog
    user_id: str
    session_id: str
    messages: List[dict]
    current_message: str
    session_turn: int

    # personalisasi
    language_pref: Optional[str]    # explicit preference if known
    preferred_response_model: Optional[str]
    profile_context: Optional[ProfileContext]
    resolved_language: Optional[str]  # outcome of resolve_language()
    linguistic_signals: Optional[dict]  # output of linguistic_enrichment_node
    single_pass_voice: bool           # Enable 1-pass voice optimization

    # safety.
    safety_flag: Optional[str]      # None | "escalate" | "crisis" | "safe"
    crisis_tier: Optional[str]      # "1" | "2" | None -- set by crisis_triage_node
    deferred_crisis_signal: bool    # True when PHQ-9 item9 routes here
    input_guardrail: Optional[dict]  # Layer 2 verdict ({decision, reason, matched})
    crisis_escalated: bool           # True when crisis_escalation_node already wrote final_response

    # mem & gen
    kg_context: Optional[str]
    url_context: Optional[str]  # Gemini url_context tool output, gemini-provider only
    retrieval_context: Optional[dict]   # structured bucket view (Phase 1/2 ranking)
    response_draft: Optional[str]
    final_response: Optional[str]

    # policy
    cbt_node_active: Optional[str]   # technique name from CBTTechnique
    cbt_directive: Optional[dict]    # CBTDecision payload for response_generator
    cbt_state: Optional[CBTState]

    # init state
    voice_state: Optional[VoiceState]

    # assess.
    phq9_state: Optional[PHQ9SessionState]
    phq9_declined_note: Optional[bool]   # True when user just declined PHQ offer this turn

    # confess space" "no-long-term-memory" "PHQ-9-gate-bypassed" "voice mode" "crisis guardrail" "flag" "active
    confession_mode: bool



def empty_phq9_state() -> PHQ9SessionState:
    """init state"""
    return PHQ9SessionState(
        phase="idle",
        tier=None,
        reason=None,
        language=None,
        offer_made_at_turn=None,
        active_item=None,
        awaiting_clarification=False,
        responses={},
        last_total=None,
        last_severity=None,
        item9_flagged=False,
        route_to_crisis_after=False,
        retry_scheduled_at=None,
        back_count=0,
        last_judge_action=None,
        last_judge_rationale=None,
        user_initiated=False,
        offer_armed=False,
    )


def empty_voice_state() -> VoiceState:
    """init state"""
    return VoiceState(
        audio_input=None,
        audio_input_mime=None,
        transcript=None,
        transcript_confidence=None,
        transcript_language=None,
        transcript_segments=None,
        output_modality="text",
        voice_id=None,
        voice_provider_id=None,
        speech_response=None,
        speech_response_tags=None,
        tts_model=None,
        tts_provider=None,
        tts_streaming=False,
        audio_output_url=None,
        audio_output_blob=None,
        audio_output_format=None,
        voice_error=None,
    )


def empty_cbt_state() -> CBTState:
    """init state"""
    return CBTState(
        last_offered=None,
        declined_last_offer=False,
        decline_streak=0,
        thought_record_active=False,
        thought_record=None,
        last_directive=None,
    )


def empty_conversation_state(
    *,
    user_id: str,
    session_id: str,
    language_pref: str | None = None,
) -> ConversationState:
    """init state"""
    return ConversationState(
        user_id=user_id,
        session_id=session_id,
        messages=[],
        current_message="",
        session_turn=0,
        language_pref=language_pref,
        preferred_response_model=None,
        profile_context=None,
        resolved_language=None,
        linguistic_signals=None,
        safety_flag=None,
        crisis_tier=None,
        deferred_crisis_signal=False,
        kg_context=None,
        url_context=None,
        retrieval_context=None,
        response_draft=None,
        final_response=None,
        cbt_node_active=None,
        cbt_directive=None,
        cbt_state=empty_cbt_state(),
        voice_state=empty_voice_state(),
        phq9_state=empty_phq9_state(),
        phq9_declined_note=None,
        confession_mode=False,
    )


__all__ = [
    "ConversationState",
    "PHQ9SessionState",
    "PHQ9Tier",
    "PHQ9Phase",
    "CBTState",
    "ProfileContext",
    "VoiceState",
    "OutputModality",
    "TTSModelChoice",
    "empty_phq9_state",
    "empty_cbt_state",
    "empty_voice_state",
    "empty_conversation_state",
]

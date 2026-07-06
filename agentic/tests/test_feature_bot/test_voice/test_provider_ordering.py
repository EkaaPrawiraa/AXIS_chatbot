"""
Tests for the LLM_PROVIDER-driven TTS/STT fallback ordering and the
auto-selected Gemini TTS style presets.

Context: the voice pipeline used to hardcode ElevenLabs -> OpenAI ->
Gemini for TTS and OpenAI -> Gemini for STT, completely independent of
which LLM_PROVIDER the deployment actually runs on. A deployment with
LLM_PROVIDER=gemini and no OpenAI key configured would always burn a
guaranteed-to-fail OpenAI attempt before ever reaching Gemini. Per
AGENTIC voice-fix decisions, ElevenLabs stays tier 0 for TTS (unrelated
to LLM_PROVIDER); the two tiers behind it are ordered by whichever
provider backs the text LLM.
"""
from __future__ import annotations

import pytest

from agentic.agent.nodes.speech_to_text import (
    GeminiTranscriptionProvider,
    OpenAITranscriptionProvider,
    _default_stt_providers,
)
from agentic.agent.nodes.text_to_speech import (
    _inject_gemini_audio_tags,
    _resolve_gemini_voice_entry,
    _select_tts_style,
    text_to_speech_node,
)
from agentic.agent.state import empty_conversation_state
from agentic.config.gemini_tts_tiers import (
    build_gemini_director_notes,
    resolve_gemini_tier,
    resolve_gemini_voice_name,
    resolve_voice_character,
)
from agentic.config.voices import load_voice_catalog
from agentic.tests.test_feature_bot.test_voice.conftest import FakeAdapterLLM


def _voice_ready(state, *, mode="v2_5_turbo", text="hai aku denger kamu"):
    state["voice_state"]["output_modality"] = "voice"
    state["voice_state"]["tts_model"] = mode
    state["voice_state"]["speech_response"] = text
    return state


class TestDefaultSTTProviderOrdering:
    def test_gemini_primary_when_llm_provider_is_gemini(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        primary, fallback = _default_stt_providers()
        assert isinstance(primary, GeminiTranscriptionProvider)
        assert isinstance(fallback, OpenAITranscriptionProvider)

    def test_openai_primary_when_llm_provider_is_openai(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        primary, fallback = _default_stt_providers()
        assert isinstance(primary, OpenAITranscriptionProvider)
        assert isinstance(fallback, GeminiTranscriptionProvider)

    def test_local_defaults_to_gemini_primary(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "local")
        primary, fallback = _default_stt_providers()
        assert isinstance(primary, GeminiTranscriptionProvider)
        assert isinstance(fallback, OpenAITranscriptionProvider)


class TestTTSProviderOrdering:
    @pytest.mark.asyncio
    async def test_gemini_tried_before_openai_when_llm_provider_is_gemini(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_gemini_tts.error = None  # let Gemini succeed on the first try
        state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
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
        assert voice["tts_provider"] == "gemini_tts"
        # OpenAI must never have been called -- Gemini succeeded first.
        assert fake_openai_tts.calls == []
        assert fake_gemini_tts.calls

    @pytest.mark.asyncio
    async def test_openai_tried_before_gemini_when_llm_provider_is_openai(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        fake_elevenlabs.error = "503 Service Unavailable"
        state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
        out = await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
        )
        voice = out["voice_state"]
        assert voice["tts_provider"] == "openai_tts1"
        # Gemini must never have been called -- OpenAI succeeded first.
        assert fake_gemini_tts.calls == []
        assert fake_openai_tts.calls


class TestSelectTTSStyle:
    """_select_tts_style now returns a bool -- whether this turn needs the
    extra empathetic modifier layered on TOP of the active voice
    character's own base style (see build_gemini_director_notes)."""

    def test_crisis_safety_flag_is_empathetic(self) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["safety_flag"] = "crisis"
        assert _select_tts_style(state) is True

    def test_escalate_safety_flag_is_empathetic(self) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["safety_flag"] = "escalate"
        assert _select_tts_style(state) is True

    def test_active_cbt_technique_is_empathetic(self) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["cbt_directive"] = {"technique": "validate", "reason": "default_validate"}
        assert _select_tts_style(state) is True

    def test_none_technique_is_not_empathetic(self) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["cbt_directive"] = {"technique": "none", "reason": "casual_no_emotional_content"}
        assert _select_tts_style(state) is False

    def test_no_directive_at_all_is_not_empathetic(self) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        assert _select_tts_style(state) is False


class TestBuildGeminiDirectorNotes:
    def test_known_character_uses_its_own_style_and_pacing(self) -> None:
        notes = build_gemini_director_notes("ceria", empathetic=False)
        assert "Upbeat, bright, and playful" in notes
        assert "Natural to brisk" in notes
        assert "Right now, prioritize gentleness" not in notes

    def test_unknown_character_falls_back_to_neutral_default(self) -> None:
        notes = build_gemini_director_notes(None, empathetic=False)
        assert "Calm, steady, and grounded" in notes  # "tenang" default

    def test_empathetic_appends_the_gentleness_modifier(self) -> None:
        notes = build_gemini_director_notes("ceria", empathetic=True)
        assert "Upbeat, bright, and playful" in notes  # character style kept
        assert "Right now, prioritize gentleness" in notes


class TestResolveVoiceCharacter:
    def test_known_voice_names_resolve_to_their_character(self) -> None:
        assert resolve_voice_character("Sulafat") == "hangat"
        assert resolve_voice_character("achird") == "hangat"
        assert resolve_voice_character("Enceladus") == "tenang"
        assert resolve_voice_character("Puck") == "ceria"
        assert resolve_voice_character("Charon") == "perangkat"

    def test_unknown_or_missing_voice_returns_none(self) -> None:
        assert resolve_voice_character("alloy") is None
        assert resolve_voice_character(None) is None


class TestGeminiTierResolution:
    def test_known_tier_ids_resolve_to_themselves(self) -> None:
        tier = resolve_gemini_tier("gemini-3.1-flash-tts-preview")
        assert tier.model == "gemini-3.1-flash-tts-preview"
        assert tier.female_voice == "Puck"
        assert tier.male_voice == "Fenrir"

    def test_looser_alias_ids_resolve_correctly(self) -> None:
        tier = resolve_gemini_tier("gemini-2.5-pro-tts")
        assert tier.model == "gemini-2.5-pro-preview-tts"
        assert tier.female_voice == "Aoede"
        assert tier.male_voice == "Enceladus"

    def test_unknown_id_falls_back_to_default_tier(self) -> None:
        tier = resolve_gemini_tier("not-a-real-tier")
        assert tier.model == "gemini-2.5-flash-preview-tts"

    def test_none_falls_back_to_default_tier(self) -> None:
        tier = resolve_gemini_tier(None)
        assert tier.model == "gemini-2.5-flash-preview-tts"

    def test_gender_selects_correct_voice(self) -> None:
        tier = resolve_gemini_tier("gemini-2.5-flash-preview-tts")
        assert resolve_gemini_voice_name(tier, "wanita") == "Leda"
        assert resolve_gemini_voice_name(tier, "pria") == "Charon"
        # Missing/unrecognized gender defaults to female.
        assert resolve_gemini_voice_name(tier, None) == "Leda"


class TestResolveGeminiVoiceEntry:
    """
    End-to-end check of the path the Settings tier+gender picker actually
    exercises: the frontend sends the resolved Gemini prebuilt voice name
    (e.g. "Enceladus") directly as voice_id. That id isn't a catalog
    persona, so VoiceCatalog.get() falls into its "unknown voice_id -- use
    as a raw provider id" path (persona="user-selected"), and
    _resolve_gemini_voice_entry must then use it AS-IS rather than
    substituting the tier's default female voice.
    """

    def test_raw_voice_id_from_picker_is_used_as_is(self) -> None:
        catalog = load_voice_catalog(force_reload=True)
        voice_entry = catalog.get("Enceladus", language="id")
        assert voice_entry.persona == "user-selected"

        resolved = _resolve_gemini_voice_entry(voice_entry, "gemini-2.5-pro-tts")
        assert resolved.id == "Enceladus"

    def test_catalog_persona_falls_back_to_tier_default(self) -> None:
        catalog = load_voice_catalog(force_reload=True)
        voice_entry = catalog.get("nura_warm_female", language="id")
        assert voice_entry.persona != "user-selected"

        resolved = _resolve_gemini_voice_entry(voice_entry, "gemini-2.5-pro-tts")
        assert resolved.id == "Aoede"  # gemini-2.5-pro-tts's default (female) voice

    def test_missing_voice_id_falls_back_to_tier_default(self) -> None:
        catalog = load_voice_catalog(force_reload=True)
        voice_entry = catalog.get(None, language="id")

        resolved = _resolve_gemini_voice_entry(voice_entry, "gemini-3.1-flash-tts")
        assert resolved.id == "Puck"  # gemini-3.1-flash-tts's default (female) voice

    def test_foreign_provider_voice_id_falls_back_to_tier_default(self) -> None:
        """"alloy" (ElevenLabs/OpenAI's own default voice_id, and the
        frontend's literal default for any profile that hasn't touched
        the voice-character picker yet) isn't a catalog persona either,
        so it also lands in the "user-selected" fallback path -- but it
        is NOT a real Gemini voice name, and passing it straight through
        gets flatly rejected by Gemini's API ("Voice name alloy is not
        supported"). Live-verified in production: this was the reason a
        default profile's ElevenLabs-fails -> Gemini-fallback leg always
        failed too, cascading down to the OpenAI leg on every single
        request."""
        catalog = load_voice_catalog(force_reload=True)
        voice_entry = catalog.get("alloy", language="id")
        assert voice_entry.persona == "user-selected"

        resolved = _resolve_gemini_voice_entry(voice_entry, "gemini-2.5-pro-tts")
        assert resolved.id == "Aoede"  # gemini-2.5-pro-tts's default (female) voice


class TestGeminiTierGetsDirectorNotesAndTags:
    """End-to-end check that _try_gemini actually wires the character's
    Director's Notes (Style/Accent/Pacing) into `instructions`, and runs
    the plain text through _inject_gemini_audio_tags before handing it to
    GeminiTTSClient.synthesize -- not just that resolve/build helpers work
    in isolation (covered above)."""

    @pytest.mark.asyncio
    async def test_director_notes_reflect_the_resolved_character(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_gemini_tts.error = None
        state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
        state["voice_state"]["voice_id"] = "Puck"  # "ceria" character
        await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(),
        )
        instructions = fake_gemini_tts.calls[0]["instructions"]
        assert "Upbeat, bright, and playful" in instructions  # "ceria" style
        assert "Right now, prioritize gentleness" not in instructions

    @pytest.mark.asyncio
    async def test_crisis_turn_adds_empathetic_modifier_on_top_of_character(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_gemini_tts.error = None
        state = _voice_ready(empty_conversation_state(user_id="u", session_id="s"))
        state["voice_state"]["voice_id"] = "Puck"  # "ceria" character
        state["safety_flag"] = "crisis"
        await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(),
        )
        instructions = fake_gemini_tts.calls[0]["instructions"]
        assert "Upbeat, bright, and playful" in instructions  # character kept
        assert "Right now, prioritize gentleness" in instructions  # modifier added

    @pytest.mark.asyncio
    async def test_tagged_text_from_the_llm_reaches_gemini_synthesize(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_gemini_tts.error = None
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            text="Hai, aku denger kamu kok.",
        )
        await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(reply="[warmly] Hai, aku denger kamu kok."),
        )
        assert fake_gemini_tts.calls[0]["text"] == "[warmly] Hai, aku denger kamu kok."

    @pytest.mark.asyncio
    async def test_tag_injection_failure_falls_back_to_plain_text(
        self, audit, fake_elevenlabs, fake_openai_tts, fake_gemini_tts, voice_catalog,
        monkeypatch,
    ) -> None:
        """A broken tag-injection LLM must never block synthesis -- Gemini
        still gets the plain, untagged text."""
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        fake_elevenlabs.error = "503 Service Unavailable"
        fake_gemini_tts.error = None
        state = _voice_ready(
            empty_conversation_state(user_id="u", session_id="s"),
            text="Hai, aku denger kamu kok.",
        )
        await text_to_speech_node(
            state,
            elevenlabs=fake_elevenlabs,
            openai_tts=fake_openai_tts,
            gemini_tts=fake_gemini_tts,
            catalog=voice_catalog,
            audit=audit,
            gemini_tag_llm=FakeAdapterLLM(error=True),
        )
        assert fake_gemini_tts.calls[0]["text"] == "Hai, aku denger kamu kok."


class TestInjectGeminiAudioTags:
    @pytest.mark.asyncio
    async def test_empty_text_returns_unchanged_without_calling_llm(self) -> None:
        llm = FakeAdapterLLM()
        result = await _inject_gemini_audio_tags("   ", llm=llm)
        assert result == "   "
        assert llm.calls == []

    @pytest.mark.asyncio
    async def test_llm_reply_is_used_as_the_tagged_text(self) -> None:
        llm = FakeAdapterLLM(reply="[giggles] Wkwk lucu banget itu.")
        result = await _inject_gemini_audio_tags("Wkwk lucu banget itu.", llm=llm)
        assert result == "[giggles] Wkwk lucu banget itu."

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_the_plain_input(self) -> None:
        llm = FakeAdapterLLM(error=True)
        result = await _inject_gemini_audio_tags("Halo, aku AXIS.", llm=llm)
        assert result == "Halo, aku AXIS."

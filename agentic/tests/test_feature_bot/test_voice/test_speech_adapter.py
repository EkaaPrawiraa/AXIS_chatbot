"""test node"""

from __future__ import annotations

import pytest

from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.speech_adapter import (
    V3_TECHNIQUES,
    select_mode,
    speech_adapter_node,
)
from agentic.agent.state import empty_conversation_state


def _voice_state(state, *, modality="voice"):
    state["voice_state"]["output_modality"] = modality
    return state


class TestModeSelection:
    def test_default_is_v25(self) -> None:
        assert select_mode({"cbt_node_active": "validate"}) == "v2_5_turbo"

    def test_grounding_is_v3(self) -> None:
        assert select_mode({"cbt_node_active": CBTTechnique.GROUNDING.value}) == "v3"

    def test_v3_set_membership(self) -> None:
        assert CBTTechnique.GROUNDING.value in V3_TECHNIQUES


class TestNode:
    @pytest.mark.asyncio
    async def test_text_modality_skips(self, audit, adapter_llm_v25) -> None:
        state = empty_conversation_state(user_id="u", session_id="s")
        state["voice_state"]["output_modality"] = "text"
        state["final_response"] = "Saya mengerti, ini berat."
        out = await speech_adapter_node(
            state, audit=audit, llm_v25=adapter_llm_v25,
        )
        assert out["voice_state"]["speech_response"] is None
        assert adapter_llm_v25.calls == []

    @pytest.mark.asyncio
    async def test_v25_default_path(self, audit, adapter_llm_v25) -> None:
        state = _voice_state(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        state["final_response"] = "Saya memahami bahwa hal tersebut berat."
        out = await speech_adapter_node(
            state, audit=audit, llm_v25=adapter_llm_v25,
        )
        voice = out["voice_state"]
        assert voice["tts_model"] == "v2_5_turbo"
        assert voice["speech_response"]
        assert voice["speech_response_tags"] is None
        assert audit.has_type("speech_adapted_v2_5_turbo")
        assert adapter_llm_v25.calls

    @pytest.mark.asyncio
    async def test_language_policy_is_sent_to_adapter(
        self, audit, adapter_llm_v25,
    ) -> None:
        state = _voice_state(
            empty_conversation_state(user_id="u", session_id="s", language_pref="en"),
        )
        state["resolved_language"] = "en"
        state["current_message"] = "I feel tired but aku masih trying."
        state["linguistic_signals"] = {"language": "mixed"}
        state["final_response"] = "I hear you, and we can take this slowly."
        await speech_adapter_node(
            state, audit=audit, llm_v25=adapter_llm_v25,
        )
        human_message = adapter_llm_v25.calls[0][1].content
        assert "LANGUAGE POLICY" in human_message
        assert "If the user used English" in human_message
        assert "code-switched" in human_message
        assert "detected_user_language=mixed" in human_message
        assert "I feel tired but aku masih trying." in human_message

    @pytest.mark.asyncio
    async def test_grounding_uses_v3_with_tags(
        self, audit, adapter_llm_v25, adapter_llm_v3,
    ) -> None:
        state = _voice_state(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        state["cbt_node_active"] = CBTTechnique.GROUNDING.value
        state["final_response"] = (
            "Mari ambil napas pelan-pelan dan rasakan tubuhmu di kursi."
        )
        out = await speech_adapter_node(
            state, audit=audit, llm_v25=adapter_llm_v25, llm_v3=adapter_llm_v3,
        )
        voice = out["voice_state"]
        assert voice["tts_model"] == "v3"
        assert voice["speech_response_tags"]
        assert "[softly]" in voice["speech_response_tags"]
        # safety_net
        assert voice["speech_response"]
        assert "[" not in voice["speech_response"]
        assert audit.has_type("speech_adapted_v3")

    @pytest.mark.asyncio
    async def test_falls_back_when_llm_fails(self, audit) -> None:
        from agentic.tests.test_feature_bot.test_voice.conftest import (
            FakeAdapterLLM,
        )

        broken = FakeAdapterLLM(error=True)
        state = _voice_state(
            empty_conversation_state(user_id="u", session_id="s"),
        )
        state["final_response"] = "Saya mengerti — ini hal berat."
        out = await speech_adapter_node(
            state, audit=audit, llm_v25=broken,
        )
        voice = out["voice_state"]
        assert voice["speech_response"]
        assert voice["voice_error"]

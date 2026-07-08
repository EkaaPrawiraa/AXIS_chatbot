"""test layer 3 pre-gen crisis"""

from __future__ import annotations

import pytest

from agentic.agent.nodes.crisis_guardrail import (
    crisis_escalation_node,
    crisis_guardrail_node,
    evaluate_pregen,
    load_crisis_resources,
    load_pregen_rules,
    render_resource_block,
    render_crisis_response,
)
from agentic.agent.state import empty_conversation_state, empty_phq9_state



class TestPreGenCheck:
    def test_phrase_overlap_triggers(self) -> None:
        rules = load_pregen_rules(force_reload=True)
        # skip to next
        msg = "ingin mengakhiri hidupnya sekarang"
        verdict = evaluate_pregen(msg, rules=rules)
        assert verdict.crisis is True
        assert verdict.matched_phrase is not None
        assert verdict.similarity >= rules.threshold

    def test_unrelated_message_does_not_trigger(self) -> None:
        verdict = evaluate_pregen("halo, hari ini gimana?")
        assert verdict.crisis is False
        assert verdict.similarity < 0.5

    def test_empty_message(self) -> None:
        verdict = evaluate_pregen("")
        assert verdict.crisis is False
        assert verdict.similarity == 0.0



class TestPreGenNode:
    @pytest.mark.asyncio
    async def test_idle_phq9_sets_safety_flag(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        state["current_message"] = "ingin mengakhiri hidupnya"
        await crisis_guardrail_node(state, audit=audit)
        assert state.get("safety_flag") == "crisis"
        assert any(e.event_type == "semantic_crisis" for e in audit.events)

    @pytest.mark.asyncio
    async def test_phq9_in_progress_defers_crisis(self, audit) -> None:
        """`while phq9_in_flight`"""
        state = empty_conversation_state(user_id="u1", session_id="s1")
        state["current_message"] = "ingin mengakhiri hidupnya"
        phq = empty_phq9_state()
        phq["phase"] = "in_progress"
        phq["active_item"] = 4
        state["phq9_state"] = phq

        await crisis_guardrail_node(state, audit=audit)
        assert state.get("safety_flag") != "crisis", (
            "crisis must defer while PHQ-9 is active"
        )
        # audit trail
        assert any(
            e.event_type == "semantic_crisis_deferred_phq9"
            for e in audit.events
        )

    @pytest.mark.asyncio
    async def test_input_layer_already_escalated_idle_phq9(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        state["input_guardrail"] = {  # type: ignore[typeddict-unknown-key]
            "decision": "escalate_crisis",
            "reason": "crisis_keyword_id",
            "matched": "ingin mati",
        }
        await crisis_guardrail_node(state, audit=audit)
        assert state.get("safety_flag") == "crisis"

    @pytest.mark.asyncio
    async def test_input_layer_escalated_but_phq9_active(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        state["input_guardrail"] = {  # type: ignore[typeddict-unknown-key]
            "decision": "escalate_crisis",
            "reason": "crisis_keyword_id",
            "matched": "ingin mati",
        }
        phq = empty_phq9_state()
        phq["phase"] = "in_progress"
        phq["active_item"] = 4
        state["phq9_state"] = phq

        await crisis_guardrail_node(state, audit=audit)
        # finish PHQ-9
        assert state.get("safety_flag") != "crisis"



class TestCrisisEscalation:
    def test_resources_loaded(self) -> None:
        res = load_crisis_resources(force_reload=True)
        assert res.primary_name
        assert res.primary_contact
        assert {
            "primary",
            "secondary",
            "women_and_children",
            "women_crisis_center",
            "campus",
            "additional_counseling",
            "emergency",
            "reference",
        }.issubset(res.items)

    def test_render_template_includes_resources(self) -> None:
        text = render_crisis_response()
        assert "Healing119.id Hotline" in text
        assert "PSC 119" in text
        assert "LISA Suicide Prevention Helpline" in text
        assert "119" in text
        assert "+62 811 3855 472" in text
        # skip template leak
        assert "{primary_contact}" not in text
        assert "{campus_name}" not in text
        assert "{resource_lines}" not in text

    def test_tier2_resource_block_uses_system_hotline_numbers(self) -> None:
        text = render_resource_block()
        assert "Kontak bantuan dari sistem" in text
        assert "Healing119.id Hotline" in text
        assert "119" in text
        assert "LISA Suicide Prevention Helpline" in text
        assert "+62 811 3815 472" in text

    def test_contextual_resources_render_clean_nested_contacts(self) -> None:
        text = render_crisis_response(
            state={
                "current_message": (
                    "aku mahasiswa ITB butuh konseling setelah pelecehan "
                    "di kampus, ada alternatif?"
                )
            }
        )
        assert "SAPA Service 129" in text
        assert "Women's Crisis Center Jombang Helpline" in text
        assert "Bimbingan Konseling Direktorat Kemahasiswaan ITB" in text
        assert "Yayasan Pulih" in text
        assert "Find A Helpline Indonesia" in text
        assert "Email: bk@kemahasiswaan.itb.ac.id" in text
        assert "{'email'" not in text

    @pytest.mark.asyncio
    async def test_node_emits_deterministic_response(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        await crisis_escalation_node(state, audit=audit)
        assert state["crisis_escalated"] is True  # type: ignore[typeddict-item]
        assert state["safety_flag"] == "crisis"
        assert state["final_response"]
        assert "{" not in state["final_response"]

    @pytest.mark.asyncio
    async def test_node_logs_critical_event(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        await crisis_escalation_node(state, audit=audit)
        assert any(
            e.event_type == "crisis_escalation"
            and e.severity.value == "critical"
            for e in audit.events
        )

    @pytest.mark.asyncio
    async def test_phq9_item9_route_marked_in_audit(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        phq = empty_phq9_state()
        phq["phase"] = "deferred_crisis"
        phq["route_to_crisis_after"] = True
        state["phq9_state"] = phq
        await crisis_escalation_node(state, audit=audit)
        ev = next(e for e in audit.events if e.event_type == "crisis_escalation")
        assert ev.trigger_detail == "phq9_item9"

    @pytest.mark.asyncio
    async def test_phq9_item9_route_cleared_after_escalation(self, audit) -> None:
        state = empty_conversation_state(user_id="u1", session_id="s1")
        state["final_response"] = "Skor PHQ-9 kamu adalah 13."
        phq = empty_phq9_state()
        phq["phase"] = "deferred_crisis"
        phq["route_to_crisis_after"] = True
        state["phq9_state"] = phq

        await crisis_escalation_node(state, audit=audit)

        assert "Skor PHQ-9 kamu adalah 13." not in state["final_response"]
        assert state["phq9_state"]["phase"] == "completed"
        assert state["phq9_state"]["route_to_crisis_after"] is False

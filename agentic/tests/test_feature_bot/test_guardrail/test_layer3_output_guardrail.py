"""rewrited comment: "skip regex"""

from __future__ import annotations

import pytest

from agentic.agent.nodes.output_guardrail import (
    find_violations,
    load_postgen_rules,
    output_guardrail_node,
)
from agentic.agent.state import empty_conversation_state



class TestFindViolations:
    def test_diagnostic_pattern_id(self) -> None:
        text = "Berdasarkan skor kamu, kamu mengalami depresi sedang."
        violations = find_violations(text)
        assert violations
        assert any(v.category == "diagnostic" for v in violations)

    def test_phq9_association_pattern_id(self) -> None:
        text = "Skor di kisaran ini sering dikaitkan dengan depresi sedang."
        violations = find_violations(text)
        assert violations
        assert any(v.category == "diagnostic" for v in violations)

    def test_clinical_instruction_pattern_id(self) -> None:
        text = "Sebaiknya kamu konsumsi antidepresan sekarang."
        violations = find_violations(text)
        assert any(v.category == "clinical_instruction" for v in violations)

    def test_diagnostic_pattern_en(self) -> None:
        text = "Your score indicates you have moderate depression."
        violations = find_violations(text)
        assert any(v.category == "diagnostic" for v in violations)

    def test_clean_text_passes(self) -> None:
        text = (
            "Aku dengar kamu, kondisi yang kamu ceritakan terdengar berat. "
            "Kalau perlu kita bisa cerita lebih lanjut."
        )
        assert find_violations(text) == ()

    def test_loads_rules(self) -> None:
        rules = load_postgen_rules(force_reload=True)
        assert rules.diagnostic_patterns
        assert rules.clinical_patterns
        assert rules.max_attempts >= 1



def _state_with_draft(draft: str):
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["response_draft"] = draft
    return state


class TestNode:
    @pytest.mark.asyncio
    async def test_clean_draft_promoted(self, audit, clean_rewrite_llm) -> None:
        state = _state_with_draft(
            "Aku dengar kamu. Kalau perlu kita bisa cerita pelan-pelan."
        )
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=clean_rewrite_llm
        )
        assert state["final_response"] == state["response_draft"]
        assert clean_rewrite_llm.calls == []
        assert any(e.event_type == "output_clean" for e in audit.events)

    @pytest.mark.asyncio
    async def test_empty_draft_gets_fallback(self, audit, clean_rewrite_llm) -> None:
        state = _state_with_draft("")
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=clean_rewrite_llm
        )
        assert state["final_response"]
        assert any(e.event_type == "empty_response_fallback" for e in audit.events)

    @pytest.mark.asyncio
    async def test_violation_triggers_rewrite_then_passes(
        self, audit, clean_rewrite_llm
    ) -> None:
        state = _state_with_draft("Kamu mengalami depresi sedang.")
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=clean_rewrite_llm
        )
        assert clean_rewrite_llm.calls, "rewrite must be invoked"
        assert state["final_response"] != state["response_draft"]
        # clean.
        assert find_violations(state["final_response"]) == ()
        assert any(e.event_type == "rewrite_success" for e in audit.events)

    @pytest.mark.asyncio
    async def test_rewrite_loop_exhaustion_falls_back(
        self, audit, stubborn_rewrite_llm
    ) -> None:
        state = _state_with_draft("Kamu mengalami depresi sedang.")
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=stubborn_rewrite_llm
        )
        # fallback msg uses std phrasing.
        assert state["final_response"]
        assert "konselor" in state["final_response"].lower() or \
               "profesional" in state["final_response"].lower()
        assert any(e.event_type == "safe_fallback" for e in audit.events)

    @pytest.mark.asyncio
    async def test_broken_llm_falls_back(
        self, audit, broken_rewrite_llm
    ) -> None:
        state = _state_with_draft("Kamu mengalami depresi sedang.")
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=broken_rewrite_llm
        )
        assert state["final_response"]
        assert any(e.event_type == "safe_fallback" for e in audit.events)

    @pytest.mark.asyncio
    async def test_crisis_response_skipped(self, audit, clean_rewrite_llm) -> None:
        """skip"""
        state = _state_with_draft("Kamu mengalami depresi sedang.")
        state["crisis_escalated"] = True  # type: ignore[typeddict-unknown-key]
        state["final_response"] = "deterministic crisis text"
        await output_guardrail_node(
            state, audit=audit, rewrite_llm=clean_rewrite_llm
        )
        assert state["final_response"] == "deterministic crisis text"
        assert clean_rewrite_llm.calls == []

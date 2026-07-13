"""routing"""

from __future__ import annotations

import pytest

from agentic.agent.graph import (
    route_after_dialogue,
    route_after_output_guardrail as route_after_guardrail,
)
from agentic.agent.state import empty_phq9_state


# route


class TestRouteAfterDialogue:
    def test_offer_pending_routes_to_response_generator(self) -> None:
        phq9 = empty_phq9_state()
        phq9["phase"] = "offer_pending"
        assert route_after_dialogue({"phq9_state": phq9}) == "response_generator"

    @pytest.mark.parametrize(
        "phase",
        ["offered", "in_progress", "awaiting_clar"],
    )
    def test_active_phases_route_to_phq9(self, phase: str) -> None:
        phq9 = empty_phq9_state()
        phq9["phase"] = phase  # type: ignore[assignment]
        assert route_after_dialogue({"phq9_state": phq9}) == "phq9_delivery"

    @pytest.mark.parametrize(
        "phase",
        ["idle", "completed", "declined", "deferred_crisis"],
    )
    def test_terminal_phases_route_to_response(self, phase: str) -> None:
        phq9 = empty_phq9_state()
        phq9["phase"] = phase  # type: ignore[assignment]
        assert route_after_dialogue({"phq9_state": phq9}) == "response_generator"

    def test_no_phq9_state_routes_to_response(self) -> None:
        assert route_after_dialogue({}) == "response_generator"


# buat ngelip


class TestRouteAfterGuardrail:
    def test_routes_to_crisis_when_flagged(self) -> None:
        phq9 = empty_phq9_state()
        phq9["route_to_crisis_after"] = True
        assert route_after_guardrail({"phq9_state": phq9}) == "crisis_escalation"

    def test_routes_to_session_end_when_clear(self) -> None:
        phq9 = empty_phq9_state()
        phq9["route_to_crisis_after"] = False
        assert route_after_guardrail({"phq9_state": phq9}) == "session_end"

    def test_no_state_defaults_to_session_end(self) -> None:
        assert route_after_guardrail({}) == "session_end"

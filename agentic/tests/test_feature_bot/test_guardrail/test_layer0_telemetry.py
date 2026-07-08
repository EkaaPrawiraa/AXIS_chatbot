"""test logger test dataclasses"""

from __future__ import annotations

import pytest

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    NullGuardrailLogger,
)


class TestGuardrailEvent:
    def test_to_log_line_includes_layer_and_decision(self) -> None:
        ev = GuardrailEvent(
            user_id="u1",
            session_id="s1",
            layer=GuardrailEventLayer.INPUT,
            event_type="crisis_keyword_id",
            decision=GuardrailEventDecision.ESCALATE,
            severity=GuardrailEventSeverity.CRITICAL,
            trigger_detail="ingin mati",
            latency_ms=2,
        )
        line = ev.to_log_line()
        assert "layer=input" in line
        assert "decision=escalate" in line
        assert "severity=critical" in line
        assert "type=crisis_keyword_id" in line


class TestNullLogger:
    @pytest.mark.asyncio
    async def test_records_in_memory(self) -> None:
        logger = NullGuardrailLogger()
        ev = GuardrailEvent(
            user_id=None,
            session_id=None,
            layer=GuardrailEventLayer.POST_GEN,
            event_type="rewrite_success",
            decision=GuardrailEventDecision.REWRITE,
        )
        await logger.log(ev)
        assert logger.events == [ev]

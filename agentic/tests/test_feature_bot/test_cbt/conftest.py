"""btwn ctb"""

from __future__ import annotations

import pytest

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    NullGuardrailLogger,
)


class RecordingAuditLogger(NullGuardrailLogger):
    """buat nyimpen"""

    def by_type(self, event_type: str) -> list[GuardrailEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def technique_events(self) -> list[GuardrailEvent]:
        return [e for e in self.events if e.event_type.startswith("cbt_")]


@pytest.fixture
def audit() -> RecordingAuditLogger:
    return RecordingAuditLogger()

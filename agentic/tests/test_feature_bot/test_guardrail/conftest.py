"""Shared fakes for the guardrail test suite."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailLogger,
    NullGuardrailLogger,
)



class RecordingAuditLogger(NullGuardrailLogger):
    """A NullGuardrailLogger that stores events for assertions."""

    def __init__(self) -> None:
        super().__init__()

    def by_type(self, event_type: str) -> list[GuardrailEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def by_layer(self, layer: str) -> list[GuardrailEvent]:
        return [e for e in self.events if e.layer.value == layer]



class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeRewriteLLM:
    """
    Minimal fake for the rewrite LLM. Returns the next reply from
    ``replies`` on each call, falling back to a clean default.

    ``calls`` records each invocation for assertions.
    """

    replies: list[str] = field(default_factory=list)
    default: str = "Aku dengar kamu. Mari kita lanjut bicara pelan-pelan."
    calls: list[list[Any]] = field(default_factory=list)

    async def ainvoke(self, messages: list[Any]) -> _FakeAIMessage:
        self.calls.append(messages)
        if self.replies:
            return _FakeAIMessage(self.replies.pop(0))
        return _FakeAIMessage(self.default)


@dataclass
class FakeBrokenLLM:
    """LLM that always raises. Used to test fallback paths."""

    async def ainvoke(self, _messages: list[Any]) -> _FakeAIMessage:
        raise RuntimeError("simulated llm failure")



@pytest.fixture
def audit() -> RecordingAuditLogger:
    return RecordingAuditLogger()


@pytest.fixture
def clean_rewrite_llm() -> FakeRewriteLLM:
    return FakeRewriteLLM(
        replies=[
            "Aku dengar kamu. Kondisi yang kamu ceritakan terdengar berat. "
            "Kalau perlu, kamu bisa cerita lebih lanjut.",
        ],
    )


@pytest.fixture
def stubborn_rewrite_llm() -> FakeRewriteLLM:
    """LLM that keeps emitting violating text so the loop exhausts."""
    return FakeRewriteLLM(
        replies=[
            "Kamu mengalami depresi sedang.",
            "Skor kamu menunjukkan kamu mengalami depresi.",
            "Skor kamu menunjukkan kamu mengalami depresi sedang.",
        ],
    )


@pytest.fixture
def broken_rewrite_llm() -> FakeBrokenLLM:
    return FakeBrokenLLM()

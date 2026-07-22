"""empty kg_context, insufficient_data, no narrative, high risk."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from agentic.agent.audit.guardrail_events import GuardrailEvent, NullGuardrailLogger
from agentic.agent.nodes.understanding_synthesis import (
    UnderstandingSynthesis,
    _parse_synthesis_output,
    synthesize_understanding,
    understanding_synthesis_node,
)


class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeSynthesisLLM:
    replies: list[str] = field(default_factory=list)
    default: str = "{}"
    calls: list[list[Any]] = field(default_factory=list)

    async def ainvoke(self, messages: list[Any]) -> _FakeAIMessage:
        self.calls.append(messages)
        if self.replies:
            return _FakeAIMessage(self.replies.pop(0))
        return _FakeAIMessage(self.default)


@dataclass
class FakeBrokenLLM:
    async def ainvoke(self, _messages: list[Any]) -> _FakeAIMessage:
        raise RuntimeError("simulated llm failure")


class RecordingAuditLogger(NullGuardrailLogger):
    def by_type(self, event_type: str) -> list[GuardrailEvent]:
        return [e for e in self.events if e.event_type == event_type]


_VALID_JSON = """{
  "current_emotion": "cemas karena merasa gagal lagi",
  "unmet_need": "ingin merasa kompeten",
  "active_pattern": "gagal sekali berarti gagal selamanya",
  "grounding_experience": "presentasi ditolak dosen bulan lalu",
  "possible_explanations": [
    {"hypothesis": "perfeksionisme akademik", "weight": 0.6},
    {"hypothesis": "tekanan keluarga", "weight": 0.4}
  ],
  "triggering_pattern": "revisi ditolak lagi",
  "unspoken_undercurrent": "takut dianggap tidak mampu",
  "response_guidance": "validasi dulu sebelum menawarkan solusi",
  "insufficient_data": false
}"""


def test_empty_kg_context_short_circuits_without_calling_llm() -> None:
    """no retrieval, no LLM, no fabricated narrative."""
    llm = FakeSynthesisLLM(replies=[_VALID_JSON])

    async def _run() -> UnderstandingSynthesis:
        state = {"kg_context": "", "current_message": "halo"}
        return await synthesize_understanding(state, llm=llm)

    import asyncio

    result = asyncio.run(_run())
    assert result.insufficient_data is True
    assert result.current_emotion is None
    assert llm.calls == []  # never invoked


def test_valid_json_parses_all_fields() -> None:
    result = _parse_synthesis_output(_VALID_JSON)
    assert result.insufficient_data is False
    assert result.current_emotion == "cemas karena merasa gagal lagi"
    assert result.grounding_experience == "presentasi ditolak dosen bulan lalu"
    assert result.possible_explanations == (
        {"hypothesis": "perfeksionisme akademik", "weight": 0.6},
        {"hypothesis": "tekanan keluarga", "weight": 0.4},
    )


def test_malformed_output_degrades_to_insufficient_data_not_a_crash() -> None:
    result = _parse_synthesis_output("this is not json at all")
    assert result.insufficient_data is True
    assert result.current_emotion is None


def test_empty_output_degrades_to_insufficient_data() -> None:
    result = _parse_synthesis_output("")
    assert result.insufficient_data is True


def test_explanation_with_bad_weight_type_keeps_hypothesis_drops_weight() -> None:
    raw = '{"possible_explanations": [{"hypothesis": "burnout", "weight": "high"}]}'
    result = _parse_synthesis_output(raw)
    assert result.possible_explanations == ({"hypothesis": "burnout", "weight": None},)


def test_llm_call_failure_degrades_to_insufficient_data() -> None:
    async def _run() -> UnderstandingSynthesis:
        state = {"kg_context": "[Focused recall]\n  - some memory", "current_message": "aku capek"}
        return await synthesize_understanding(state, llm=FakeBrokenLLM())

    import asyncio

    result = asyncio.run(_run())
    assert result.insufficient_data is True


def test_node_writes_state_and_logs_audit_event() -> None:
    llm = FakeSynthesisLLM(replies=[_VALID_JSON])
    audit = RecordingAuditLogger()

    async def _run() -> dict:
        state = {
            "kg_context": "[Focused recall]\n  - Experience: gagal presentasi",
            "current_message": "aku gagal lagi",
            "user_id": "u1",
            "session_id": "s1",
        }
        return await understanding_synthesis_node(state, llm=llm, audit=audit)

    import asyncio

    state = asyncio.run(_run())
    assert state["user_understanding"]["current_emotion"] == "cemas karena merasa gagal lagi"
    assert state["user_understanding"]["insufficient_data"] is False

    events = audit.by_type("understanding_synthesis")
    assert len(events) == 1
    assert events[0].trigger_detail == "synthesized"


def test_node_marks_insufficient_data_on_empty_context() -> None:
    audit = RecordingAuditLogger()

    async def _run() -> dict:
        state = {"kg_context": "", "current_message": "halo", "user_id": "u1", "session_id": "s1"}
        return await understanding_synthesis_node(state, llm=FakeSynthesisLLM(replies=[_VALID_JSON]), audit=audit)

    import asyncio

    state = asyncio.run(_run())
    assert state["user_understanding"]["insufficient_data"] is True
    events = audit.by_type("understanding_synthesis")
    assert events[0].trigger_detail == "insufficient_data"

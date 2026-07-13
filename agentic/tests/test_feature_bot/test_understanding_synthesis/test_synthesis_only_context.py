"""Task 2b: ThoughtRecord (kg_writer/thought_record_writer.py) and
Assessment/PHQ-9 history are real signal for understanding_synthesis's
reasoning, but must never reach response_generator -- v2 or v3 -- because
that is the layer whose output the user actually sees. The isolation is
architectural (this data never gets written into state["kg_context"] at
all), not just a prompt instruction, so the most important tests here are
negative: kg_context must never carry this content."""

from __future__ import annotations

import asyncio

import pytest

from agentic.tests.test_memory.conftest import (  # noqa: F401 -- fixtures picked up by name
    neo4j_client,
    neo4j_required,
    test_namespace,
)


@pytest.mark.asyncio
@neo4j_required
async def test_thought_record_history_is_fetched_from_kg(
    neo4j_client,
    test_namespace,
):
    from agentic.agent.nodes.understanding_synthesis import _fetch_thought_record_history

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (tr:ThoughtRecord {
            id: $tr_id, session_id: $session_id, thought: 'aku ga akan pernah lulus tepat waktu',
            distortion: 'catastrophizing', evidence_for: 'revisi lama',
            evidence_against: 'progres tetap jalan tiap minggu',
            balanced: 'aku memang telat tapi tetap maju', recorded_at: datetime(),
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT_RECORD {t_valid: datetime(), t_invalid: null}]->(tr)
        """,
        {
            "user_id": user_id, "ns": ns,
            "tr_id": f"{ns}-tr-1", "session_id": test_namespace["session_id"],
        },
    )

    records = await _fetch_thought_record_history(user_id)
    assert len(records) == 1
    assert records[0]["thought"] == "aku ga akan pernah lulus tepat waktu"
    assert records[0]["balanced"] == "aku memang telat tapi tetap maju"


@pytest.mark.asyncio
@neo4j_required
async def test_thought_record_never_appears_in_shared_kg_context(
    neo4j_client,
    test_namespace,
    monkeypatch,
):
    """The core architectural guarantee: even though a ThoughtRecord node
    exists for this user, build_context() (which feeds BOTH response_
    generator and, via kg_context, understanding_synthesis) must never
    surface it -- that data only reaches understanding_synthesis through
    the separate, private build_synthesis_only_context channel."""
    from agentic.memory.context_builder import build_context

    user_id = test_namespace["user_id"]
    ns = test_namespace["namespace"]

    await neo4j_client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (tr:ThoughtRecord {
            id: $tr_id, session_id: $session_id, thought: 'satu-satunya rahasia thought record',
            distortion: 'labeling', evidence_for: 'x', evidence_against: 'y',
            balanced: 'balanced-rahasia-unik-123', recorded_at: datetime(),
            test_namespace: $ns
        })
        CREATE (u)-[:HAS_THOUGHT_RECORD {t_valid: datetime(), t_invalid: null}]->(tr)
        """,
        {
            "user_id": user_id, "ns": ns,
            "tr_id": f"{ns}-tr-isolated", "session_id": test_namespace["session_id"],
        },
    )

    async def _fake_search_memory(*args, **kwargs):
        return []

    async def _fake_search_experience(*args, **kwargs):
        return []

    monkeypatch.setattr("agentic.memory.context_builder.search_memory", _fake_search_memory)
    monkeypatch.setattr("agentic.memory.context_builder.search_experience", _fake_search_experience)

    ctx = await build_context(user_id=user_id, query_embedding=[0.0] * 8, query_text="gimana hari ini")
    block = ctx.as_prompt_block()

    assert "satu-satunya rahasia thought record" not in block
    assert "balanced-rahasia-unik-123" not in block
    assert "ThoughtRecord" not in block


def test_synthesis_only_context_renders_thought_records_and_phq9(monkeypatch) -> None:
    from agentic.agent.nodes import understanding_synthesis as mod
    from agentic.memory.assessment_repo import LastPHQ9Snapshot
    from agentic.assessment.phq9 import PHQ9Severity
    from datetime import datetime, timezone

    async def _fake_records(user_id, *, limit=3):
        return [
            {
                "thought": "aku pasti gagal sidang",
                "distortion": "catastrophizing",
                "balanced": "aku sudah siapkan revisi sebaik mungkin",
            }
        ]

    async def _fake_phq9(user_id):
        return LastPHQ9Snapshot(
            administered_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            total_score=8,
            severity=PHQ9Severity.MODERATE,
            item_scores=(1, 1, 1, 1, 1, 1, 1, 1, 0),
            delta_from_prev=-4,
        )

    monkeypatch.setattr(mod, "_fetch_thought_record_history", _fake_records)
    monkeypatch.setattr(mod, "_fetch_phq9_snapshot", _fake_phq9)

    block = asyncio.run(mod.build_synthesis_only_context("u1"))

    assert "[CBT & Assessment History -- internal only]" in block
    assert "aku pasti gagal sidang" in block
    assert "aku sudah siapkan revisi sebaik mungkin" in block
    assert "severity=moderate" in block
    assert "trend=improving" in block


def test_synthesis_only_context_empty_when_no_history(monkeypatch) -> None:
    from agentic.agent.nodes import understanding_synthesis as mod

    async def _empty_records(user_id, *, limit=3):
        return []

    async def _none_phq9(user_id):
        return None

    monkeypatch.setattr(mod, "_fetch_thought_record_history", _empty_records)
    monkeypatch.setattr(mod, "_fetch_phq9_snapshot", _none_phq9)

    block = asyncio.run(mod.build_synthesis_only_context("u1"))
    assert block == ""


def test_synthesize_understanding_includes_private_context_in_prompt(monkeypatch) -> None:
    """The private context must actually reach the LLM call, not just
    exist as a formatted string nobody uses."""
    from agentic.agent.nodes import understanding_synthesis as mod

    async def _fake_synthesis_context(user_id):
        return "[CBT & Assessment History -- internal only]\nseverity=mild, trend=stable"

    monkeypatch.setattr(mod, "build_synthesis_only_context", _fake_synthesis_context)

    class _FakeAI:
        content = '{"insufficient_data": false, "current_emotion": "tenang"}'

    class _FakeLLM:
        def __init__(self):
            self.seen_prompt = None

        async def ainvoke(self, messages):
            self.seen_prompt = messages[-1].content
            return _FakeAI()

    llm = _FakeLLM()
    state = {
        "kg_context": "[Focused recall]\n  - some memory",
        "current_message": "gimana ya",
        "user_id": "u1",
    }
    result = asyncio.run(mod.synthesize_understanding(state, llm=llm))

    assert result.insufficient_data is False
    assert llm.seen_prompt is not None
    assert "severity=mild, trend=stable" in llm.seen_prompt

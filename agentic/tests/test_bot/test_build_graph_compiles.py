"""build_graph() compiles."""
from __future__ import annotations

from agentic.agent.graph import build_graph
from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.state import ConversationState


class _FakeAssessmentRepo:
    async def get_last_phq9(self, user_id):
        return None

    async def get_conversation_count(self, user_id):
        return 0

    async def get_pending_retry(self, user_id):
        return None

    async def get_distress_snapshot(self, user_id):
        return None


def _compile_graph():
    return build_graph(
        assessment_repo=_FakeAssessmentRepo(),
        audit_logger=NullGuardrailLogger(),
        activity_repo=None,
        voice_catalog=None,
        stt_provider=None,
        elevenlabs_tts=None,
        openai_tts=None,
        context_builder=None,
        response_llm=None,
        response_tools=[],
    )


def test_build_graph_compiles_without_raising():
    graph = _compile_graph()
    assert graph is not None


def test_no_node_name_collides_with_a_conversation_state_key():
    graph = _compile_graph()
    node_names = set(graph.nodes.keys()) - {"__start__"}
    state_keys = set(ConversationState.__annotations__.keys())

    collisions = node_names & state_keys
    assert not collisions, (
        f"Graph node name(s) {collisions} also exist as ConversationState "
        "key(s) -- LangGraph's add_node rejects this at compile time, and "
        "because the graph compiles lazily on first request, this only "
        "fails on a real request, not at import time."
    )

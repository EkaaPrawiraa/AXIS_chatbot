"""
Regression test: build_graph() must actually compile.

This caught a real production incident: the graph registered a node
named "input_guardrail" (agent/graph.py), which is also a top-level
ConversationState key (agent/state.py). LangGraph's StateGraph.add_node
rejects any node name that collides with a state schema key --
`ValueError: 'input_guardrail' is already being used as a state key`.

Because this is a lazy, cached compile (ChatGraphService._build_graph_once
only runs on the first request and memoizes the result), the failure
never showed up at import time or in unit tests that mock the graph --
only on the first real /chat/stream request in production, after the SSE
response had already started. Every chat message failed until fixed.

This test exercises the two things that would have caught it:
1. build_graph() actually compiles without raising.
2. No ConversationState key is ever reused as a node name -- a general
   invariant so this exact class of bug can't silently reappear if a
   future state field happens to match a future node name.
"""
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

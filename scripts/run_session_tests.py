"""
Standalone tests for memory_retrieval, response_generator,
session_end, finalizer, and sweeper.
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/sessions/focused-dreamy-albattani/mnt/CompanionshipChatBot")
sys.path.insert(0, str(ROOT))

# Disable real context_builder import attempt in retrieval node
os.environ["AGENTIC_DISABLE_CONTEXT_BUILDER"] = "1"

from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.memory_retrieval import (
    SHORT_TERM_TURN_PAIRS,
    memory_retrieval_node,
)
from agentic.agent.nodes.onboarding_check import onboarding_check_node
from agentic.agent.nodes.reminder import reminder_node
from agentic.agent.nodes.response_generator import response_generator_node
from agentic.agent.nodes.session_end import session_end_node
from agentic.agent.session.activity_repo import (
    InMemorySessionActivityRepository,
)
from agentic.agent.session.finalizer import (
    FinalizationResult,
    SessionFinalizer,
)
from agentic.agent.session.sweeper import SessionSweeper, SweeperConfig
from agentic.agent.state import empty_conversation_state


PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def t(name: str):
    def deco(fn):
        async def runner():
            try:
                if asyncio.iscoroutinefunction(fn):
                    await fn()
                else:
                    fn()
                PASSED.append(name)
                print(f"  PASS  {name}")
            except Exception as exc:
                FAILED.append((name, traceback.format_exc()))
                print(f"  FAIL  {name}: {exc!r}")
        runner.__name__ = fn.__name__
        return runner
    return deco


def section(label: str) -> None:
    print(f"\n=== {label} ===")



class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeChatLLM:
    reply: str = "Aku denger kamu, hari ini berat ya."
    error: bool = False
    calls: list[Any] = field(default_factory=list)

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.error:
            raise RuntimeError("simulated llm failure")
        return _FakeAIMessage(self.reply)



@t("memory retrieval skips on crisis")
async def test_memory_skip_crisis():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["safety_flag"] = "crisis"
    out = await memory_retrieval_node(state, audit=NullGuardrailLogger())
    assert out.get("kg_context") in (None, "")


@t("memory retrieval skips while phq9 active")
async def test_memory_skip_phq9():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["phq9_state"] = {"phase": "in_progress"}
    out = await memory_retrieval_node(state, audit=NullGuardrailLogger())
    assert out.get("kg_context") in (None, "")


@t("memory retrieval combines long+short term")
async def test_memory_combine():
    async def fake_builder(*, user_id, session_id, query, language):
        return "## Past experiences\n- Final exam stress (last month)"

    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "hari ini capek banget"
    state["messages"] = [
        {"role": "user", "content": "kemarin tidur cuma 4 jam"},
        {"role": "assistant", "content": "wajar capek, mau cerita lebih?"},
    ]
    out = await memory_retrieval_node(
        state,
        context_builder=fake_builder,
        audit=NullGuardrailLogger(),
    )
    ctx = out["kg_context"]
    assert "Past experiences" in ctx
    assert "Short-term memory context" in ctx
    assert "User: kemarin tidur" in ctx


@t("memory retrieval truncates at budget")
async def test_memory_truncates():
    async def big_builder(*, user_id, session_id, query, language):
        return "x" * 8000

    state = empty_conversation_state(user_id="u", session_id="s")
    out = await memory_retrieval_node(
        state, context_builder=big_builder, audit=NullGuardrailLogger(),
    )
    assert len(out["kg_context"]) <= 6000



@t("response generator skips when crisis_escalated")
async def test_response_skip_crisis():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["crisis_escalated"] = True
    state["final_response"] = "deterministic crisis text"
    llm = FakeChatLLM()
    out = await response_generator_node(state, llm=llm)
    assert out.get("response_draft") is None
    assert llm.calls == []


@t("response generator skips when final_response already set")
async def test_response_skip_final_set():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["final_response"] = "preset"
    llm = FakeChatLLM()
    out = await response_generator_node(state, llm=llm)
    assert llm.calls == []


@t("response generator skips when phq9 owns turn")
async def test_response_skip_phq9_active():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["phq9_state"] = {"phase": "in_progress"}
    state["current_message"] = "1"
    llm = FakeChatLLM()
    out = await response_generator_node(state, llm=llm)
    assert llm.calls == []


@t("response generator drafts reply with context")
async def test_response_drafts():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "hari ini berat banget"
    state["resolved_language"] = "id"
    state["kg_context"] = (
        "=== Short-term memory context ===\nUser: capek\nAssistant: hm"
    )
    state["cbt_node_active"] = CBTTechnique.VALIDATE.value
    state["cbt_directive"] = {"payload": {}}
    llm = FakeChatLLM(reply="Aku denger ya, terdengar berat.")
    out = await response_generator_node(state, llm=llm)
    assert out["response_draft"] == "Aku denger ya, terdengar berat."
    assert llm.calls


@t("response generator binds tools and surfaces metadata")
async def test_response_tools_bound():
    from agentic.agent.audit.guardrail_events import NullGuardrailLogger

    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "halo"
    state["resolved_language"] = "id"

    bound: dict = {"tools": None}

    class FakeBoundLLM:
        async def ainvoke(self, _msgs):
            return _FakeAIMessage("halo balik")

    class FakeBindable:
        async def ainvoke(self, _msgs):
            return _FakeAIMessage("should not be reached if bind ok")

        def bind_tools(self, tools):
            bound["tools"] = tools
            return FakeBoundLLM()

    # Explicit small toolset so the test does not depend on the
    # default registry (which requires langchain_core at import time).
    explicit_tools = [
        _StubTool("dummy_a", lambda args: "a"),
        _StubTool("dummy_b", lambda args: "b"),
    ]
    audit = NullGuardrailLogger()
    out = await response_generator_node(
        state, llm=FakeBindable(), audit=audit, tools=explicit_tools,
    )
    assert out["response_draft"] == "halo balik"
    assert bound["tools"] is not None
    assert len(bound["tools"]) == 2


# Minimal stub mimicking langchain_core.tools BaseTool surface used by
# the response_generator: ``.name`` attribute + sync ``.invoke``.
class _StubTool:
    def __init__(self, name: str, fn):
        self.name = name
        self._fn = fn

    def invoke(self, args):
        return self._fn(args)


@t("response generator runs tool-call loop and surfaces final text")
async def test_response_tool_loop():
    from agentic.agent.audit.guardrail_events import NullGuardrailLogger

    echo_tool = _StubTool(
        "echo_tool", lambda args: f"echoed:{args.get('text', '')}",
    )

    class _AICall:
        def __init__(self, content: str, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    sequence = [
        _AICall("", tool_calls=[{
            "name": "echo_tool", "args": {"text": "hello"}, "id": "c1",
        }]),
        _AICall("final reply"),
    ]
    call_count = {"n": 0}

    class FakeLLM:
        async def ainvoke(self, _msgs):
            i = call_count["n"]
            call_count["n"] = i + 1
            return sequence[i]

        def bind_tools(self, _tools):
            return self

    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "what is hello echoed?"
    out = await response_generator_node(
        state, llm=FakeLLM(),
        audit=NullGuardrailLogger(),
        tools=[echo_tool],
    )
    assert out["response_draft"] == "final reply"
    assert call_count["n"] == 2


@t("response generator caps tool iterations")
async def test_response_tool_cap():
    from agentic.agent.audit.guardrail_events import NullGuardrailLogger
    from agentic.agent.nodes.response_generator import MAX_TOOL_ITERATIONS

    busy_tool = _StubTool("busy_tool", lambda args: "ok")

    class _AICall:
        def __init__(self, content: str, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    class LoopingLLM:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, _msgs):
            self.calls += 1
            return _AICall(
                "give up",
                tool_calls=[{
                    "name": "busy_tool", "args": {"text": "x"}, "id": f"c{self.calls}",
                }],
            )

        def bind_tools(self, _tools):
            return self

    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "loop please"
    llm = LoopingLLM()
    out = await response_generator_node(
        state, llm=llm,
        audit=NullGuardrailLogger(),
        tools=[busy_tool],
    )
    # The loop must terminate after MAX_TOOL_ITERATIONS+1 ainvoke calls.
    assert llm.calls == MAX_TOOL_ITERATIONS + 1
    assert out["response_draft"]


@t("response generator survives tool failure")
async def test_response_tool_failure():
    from agentic.agent.audit.guardrail_events import NullGuardrailLogger

    def _raises(_args):
        raise RuntimeError("simulated tool failure")

    broken_tool = _StubTool("broken_tool", _raises)

    class _AICall:
        def __init__(self, content: str, tool_calls=None):
            self.content = content
            self.tool_calls = tool_calls or []

    class FakeLLM:
        def __init__(self):
            self.n = 0

        async def ainvoke(self, _msgs):
            self.n += 1
            if self.n == 1:
                return _AICall("", tool_calls=[{
                    "name": "broken_tool", "args": {"text": "x"}, "id": "c1",
                }])
            return _AICall("recovered reply")

        def bind_tools(self, _tools):
            return self

    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "trigger"
    out = await response_generator_node(
        state, llm=FakeLLM(),
        audit=NullGuardrailLogger(),
        tools=[broken_tool],
    )
    assert out["response_draft"] == "recovered reply"


@t("response generator falls back when llm fails")
async def test_response_fallback():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "halo"
    state["resolved_language"] = "id"
    llm = FakeChatLLM(error=True)
    out = await response_generator_node(state, llm=llm)
    assert out["response_draft"]
    assert "id" in (out.get("resolved_language") or "id")


# Session end + activity repo


@t("session end appends user+assistant messages")
async def test_session_end_appends():
    repo = InMemorySessionActivityRepository()
    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "halo"
    state["final_response"] = "halo juga"
    out = await session_end_node(state, activity_repo=repo)
    history = out["messages"]
    assert any(m["role"] == "user" and m["content"] == "halo" for m in history)
    assert any(m["role"] == "assistant" and m["content"] == "halo juga" for m in history)


@t("session end records ai_was_last_speaker true when reply present")
async def test_session_end_ai_last():
    repo = InMemorySessionActivityRepository()
    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "halo"
    state["final_response"] = "halo juga"
    await session_end_node(state, activity_repo=repo)
    rows = await repo.find_pending(idle_threshold=timedelta(0), limit=10)
    assert any(r.session_id == "s" and r.ai_was_last_speaker for r in rows)


@t("session end without reply marks user_last")
async def test_session_end_user_last():
    repo = InMemorySessionActivityRepository()
    state = empty_conversation_state(user_id="u", session_id="s")
    state["current_message"] = "halo"
    state["final_response"] = ""
    await session_end_node(state, activity_repo=repo)
    rows = await repo.find_pending(idle_threshold=timedelta(0), limit=10)
    # ai_was_last_speaker is False so it must NOT appear in pending list
    assert not rows


@t("activity upsert resets finalized when user returns")
async def test_activity_returns():
    repo = InMemorySessionActivityRepository()
    await repo.upsert_activity(
        session_id="s", user_id="u", ai_was_last_speaker=True,
    )
    await repo.mark_finalized("s")
    # User returns
    await repo.upsert_activity(
        session_id="s", user_id="u", ai_was_last_speaker=False,
    )
    rows = await repo.find_pending(idle_threshold=timedelta(0), limit=10)
    # Not pending because ai_was_last_speaker is False now.
    assert not rows


# Sweeper + finalizer


@dataclass
class FakeFinalizer:
    """Records calls and returns either ok or error result."""

    error_for: set[str] = field(default_factory=set)
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def finalize(self, *, session_id, user_id, language=None):
        self.calls.append((session_id, user_id))
        if session_id in self.error_for:
            return FinalizationResult(
                session_id=session_id,
                summary="",
                extracted_count=0,
                error="kg_writer:simulated",
            )
        return FinalizationResult(
            session_id=session_id,
            summary="user shared exam stress",
            extracted_count=3,
        )


@t("sweeper finalizes idle sessions with ai last")
async def test_sweeper_finalizes():
    repo = InMemorySessionActivityRepository()
    past = datetime.now(timezone.utc) - timedelta(minutes=45)
    await repo.upsert_activity(
        session_id="s1", user_id="u1", ai_was_last_speaker=True, at=past,
    )
    await repo.upsert_activity(
        session_id="s2", user_id="u1", ai_was_last_speaker=False, at=past,
    )
    fin = FakeFinalizer()
    sweeper = SessionSweeper(
        repo=repo, finalizer=fin,
        config=SweeperConfig(idle_minutes=30, batch_limit=5, max_attempts=3),
    )
    handled = await sweeper.run_once()
    assert len(handled) == 1
    assert handled[0].session_id == "s1"
    rows = await repo.find_pending(idle_threshold=timedelta(0), limit=10)
    # s1 is no longer pending after finalization.
    assert not any(r.session_id == "s1" for r in rows)


@t("sweeper retries on finalizer error then gives up at max_attempts")
async def test_sweeper_retries():
    repo = InMemorySessionActivityRepository()
    past = datetime.now(timezone.utc) - timedelta(minutes=45)
    await repo.upsert_activity(
        session_id="s1", user_id="u1", ai_was_last_speaker=True, at=past,
    )
    fin = FakeFinalizer(error_for={"s1"})
    sweeper = SessionSweeper(
        repo=repo, finalizer=fin,
        config=SweeperConfig(idle_minutes=30, batch_limit=5, max_attempts=2),
    )
    await sweeper.run_once()
    await sweeper.run_once()
    # After 2 failed attempts the sweeper stops trying.
    await sweeper.run_once()
    assert len(fin.calls) == 2  # called twice, third pass skipped
    # Row still pending because never marked finalized.
    rows = await repo.find_pending(idle_threshold=timedelta(0), limit=10)
    assert any(r.session_id == "s1" for r in rows)


@t("finalizer end-to-end with fakes")
async def test_finalizer_end_to_end():
    history_data = [
        {"role": "user", "content": "aku capek banget"},
        {"role": "assistant", "content": "wajar, mau cerita lebih?"},
        {"role": "user", "content": "ujian besok rasanya berat"},
        {"role": "assistant", "content": "kamu sudah persiapan, kan?"},
    ]

    async def loader(*, session_id, user_id):
        return history_data

    async def summarizer(*, transcript, language):
        return "User mentioned exam stress and tiredness."

    extracted_calls: list[str] = []

    async def extractor(*, message, user_id, session_id, language):
        extracted_calls.append(message)
        return {"experience": {"description": message}}

    write_calls: list[dict[str, Any]] = []

    async def writer(*, user_id, session_id, summary, extracted, language):
        write_calls.append({
            "summary": summary, "n_extracted": len(extracted),
        })

    fin = SessionFinalizer(
        history_loader=loader,
        summarizer=summarizer,
        extractor=extractor,
        kg_writer=writer,
    )
    result = await fin.finalize(session_id="s", user_id="u", language="id")
    assert result.ok is True
    assert result.summary == "User mentioned exam stress and tiredness."
    assert result.extracted_count == 2  # only user messages run through extractor
    assert len(extracted_calls) == 2
    assert write_calls and write_calls[0]["n_extracted"] == 2



@t("onboarding_check sets is_onboarding for first turn")
async def test_onboarding_first_turn():
    state = empty_conversation_state(user_id="u", session_id="s")
    out = await onboarding_check_node(state)
    assert out["is_onboarding"] is True


@t("onboarding_check is False on later turns")
async def test_onboarding_later_turn():
    state = empty_conversation_state(user_id="u", session_id="s")
    state["session_turn"] = 3
    out = await onboarding_check_node(state)
    assert out["is_onboarding"] is False


@t("reminder_node passes through")
async def test_reminder_passthrough():
    state = empty_conversation_state(user_id="u", session_id="s")
    out = await reminder_node(state)
    assert out is state



async def main():
    section("Memory retrieval")
    await test_memory_skip_crisis()
    await test_memory_skip_phq9()
    await test_memory_combine()
    await test_memory_truncates()

    section("Response generator")
    await test_response_skip_crisis()
    await test_response_skip_final_set()
    await test_response_skip_phq9_active()
    await test_response_drafts()
    await test_response_tools_bound()
    await test_response_tool_loop()
    await test_response_tool_cap()
    await test_response_tool_failure()
    await test_response_fallback()

    section("Session end + activity")
    await test_session_end_appends()
    await test_session_end_ai_last()
    await test_session_end_user_last()
    await test_activity_returns()

    section("Sweeper + finalizer")
    await test_sweeper_finalizes()
    await test_sweeper_retries()
    await test_finalizer_end_to_end()

    section("Placeholders")
    await test_onboarding_first_turn()
    await test_onboarding_later_turn()
    await test_reminder_passthrough()

    print("\n" + "=" * 60)
    print(f"PASSED: {len(PASSED)}")
    print(f"FAILED: {len(FAILED)}")
    if FAILED:
        for name, tb in FAILED:
            print(f"\n--- {name} ---")
            print(tb)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

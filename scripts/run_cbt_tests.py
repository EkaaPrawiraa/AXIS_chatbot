"""
Standalone CBT test runner. Mirrors agentic/tests/test_feature_bot/test_cbt
using only the standard library so the smoke test runs without pytest.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path("/sessions/focused-dreamy-albattani/mnt/CompanionshipChatBot")
sys.path.insert(0, str(ROOT))

from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.cbt import (
    CBTTechnique,
    DISTORTIONS,
    JudgeOutcome,
    ThoughtRecordMachine,
    detect_distortion_in_text,
    route,
    route_with_llm,
)
from agentic.agent.cbt.judge import judge_technique
from agentic.agent.cbt.thought_record import (
    ThoughtRecordStep,
    ThoughtRecordSubState,
)
from agentic.agent.nodes.dialogue_policy import dialogue_policy_node
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


def _state(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "user_id": "u",
        "session_id": "s",
        "current_message": "",
        "phq9_state": {"phase": "idle"},
        "cbt_state": {},
        "kg_context": "",
        "resolved_language": "id",
    }
    base.update(kw)
    return base



@t("distortions registry has all 10")
def test_registry():
    canonical = ("catastrophizing", "all_or_nothing", "mind_reading",
                 "fortune_telling", "emotional_reasoning",
                 "should_statements", "labeling", "magnification",
                 "personalization", "overgeneralization")
    for name in canonical:
        assert name in DISTORTIONS, f"missing {name}"


@t("distortion detector cue match")
def test_detect():
    cases = [
        ("aku pasti gagal di final", "catastrophizing"),
        ("selalu kayak gini terus", "overgeneralization"),
        ("dia pasti benci aku", "mind_reading"),
        ("aku payah", "labeling"),
        ("ini salahku semua", "personalization"),
        ("seharusnya udah selesai dari kemarin", "should_statements"),
    ]
    for text, expected in cases:
        d = detect_distortion_in_text(text)
        assert d is not None, f"no match for {text!r}"
        assert d.name == expected


@t("distortion detector neutral text")
def test_detect_neutral():
    assert detect_distortion_in_text("halo, hari ini gimana?") is None



@t("router safety flag blocks")
def test_safety_flag():
    d = route(_state(safety_flag="crisis"))
    assert d.technique is CBTTechnique.NONE
    assert d.reason == "safety_flag_blocked"


@t("router phq9 active blocks")
def test_phq9_active():
    d = route(_state(phq9_state={"phase": "in_progress"}))
    assert d.technique is CBTTechnique.NONE


@t("router thought record resumes")
def test_resume_tr():
    d = route(_state(
        current_message="apapun",
        cbt_state={"thought_record_active": True},
    ))
    assert d.technique is CBTTechnique.THOUGHT_RECORD


@t("router distortion -> reframe")
def test_distortion_reframe():
    d = route(_state(current_message="aku selalu gagal"))
    assert d.technique is CBTTechnique.REFRAME
    assert d.payload.get("distortion") == "overgeneralization"


@t("router reframe request + distortion -> thought record")
def test_reframe_request_escalation():
    d = route(_state(
        current_message="aku pasti gagal final ini, bantu reframe dong",
    ))
    assert d.technique is CBTTechnique.THOUGHT_RECORD


@t("router avoidance cue -> behavior activation")
def test_avoidance_ba():
    d = route(_state(
        current_message="ga keluar kamar dan ga balas chat",
    ))
    assert d.technique is CBTTechnique.BEHAVIOR_ACTIVATION


@t("router psychoeducation")
def test_psychoed():
    d = route(_state(current_message="apa sih yang dimaksud distortion?"))
    assert d.technique is CBTTechnique.PSYCHOEDUCATION


@t("router default validate")
def test_default():
    d = route(_state(current_message="halo, hari ini gimana"))
    assert d.technique is CBTTechnique.VALIDATE


@t("router opt-out cooldown demotes to validate")
def test_optout():
    d = route(_state(
        current_message="aku selalu gagal",
        cbt_state={
            "last_offered": "reframe",
            "declined_last_offer": True,
        },
    ))
    assert d.technique is CBTTechnique.VALIDATE
    assert d.reason == "opt_out_cooldown"



@t("thought record full run with hint")
async def test_tr_full():
    machine = ThoughtRecordMachine()
    sub = ThoughtRecordSubState()
    hint = DISTORTIONS["catastrophizing"]

    turn = await machine.step(sub_state=sub, user_reply="", language="id",
                              hinted_distortion=hint)
    assert turn.next_state.step is ThoughtRecordStep.CATCH_THOUGHT

    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku pasti gagal final besok",
        language="id", hinted_distortion=hint,
    )
    assert turn.next_state.step is ThoughtRecordStep.LABEL_DISTORTION
    assert turn.next_state.thought == "aku pasti gagal final besok"

    turn = await machine.step(
        sub_state=turn.next_state, user_reply="iya",
        language="id", hinted_distortion=hint,
    )
    assert turn.next_state.distortion == "catastrophizing"
    assert turn.next_state.step is ThoughtRecordStep.EVIDENCE_FOR

    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku belum belajar",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.EVIDENCE_AGAINST

    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku tetap dapat nilai bagus di kuis sebelumnya",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.BALANCED_THOUGHT

    turn = await machine.step(
        sub_state=turn.next_state,
        user_reply="aku belum siap sepenuhnya tapi masih bisa lulus",
        language="id",
    )
    assert turn.next_state.step is ThoughtRecordStep.DONE
    assert turn.completed is True


@t("thought record persistence round trip")
def test_tr_persist():
    sub = ThoughtRecordSubState(
        step=ThoughtRecordStep.EVIDENCE_FOR,
        thought="aku pasti gagal",
        distortion="catastrophizing",
    )
    rehydrated = ThoughtRecordSubState.from_dict(sub.to_dict())
    assert rehydrated.step is ThoughtRecordStep.EVIDENCE_FOR
    assert rehydrated.distortion == "catastrophizing"


@t("thought record english language")
async def test_tr_en():
    machine = ThoughtRecordMachine()
    turn = await machine.step(
        sub_state=ThoughtRecordSubState(),
        user_reply="", language="en",
    )
    assert "thought" in turn.bot_prompt.lower()



@t("node default validate sets state")
async def test_node_default():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "halo, hari ini gimana"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "validate"
    assert out["cbt_directive"]["technique"] == "validate"


@t("node distortion offers reframe")
async def test_node_reframe():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "aku selalu gagal di mata kuliah ini"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "reframe"
    assert out["cbt_state"]["last_offered"] == "reframe"


@t("node safety flag blocks")
async def test_node_safety():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "apapun"
    state["safety_flag"] = "crisis"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "none"


@t("node phq9 active blocks")
async def test_node_phq9():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "aku selalu gagal"
    state["phq9_state"] = {"phase": "in_progress"}
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "none"


@t("node decline marks state")
async def test_node_decline_marks():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "ga usah deh"
    state["cbt_state"] = {"last_offered": "reframe"}
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_state"]["declined_last_offer"] is True
    assert out["cbt_state"]["decline_streak"] == 1


@t("node post-decline cooldown to validate")
async def test_node_cooldown():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "aku selalu gagal"
    state["cbt_state"] = {
        "last_offered": "reframe",
        "declined_last_offer": True,
        "decline_streak": 1,
    }
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "validate"
    assert out["cbt_directive"]["reason"] == "opt_out_cooldown"


@t("node thought record start emits step + prompt")
async def test_node_tr_start():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "aku pasti gagal final, bantu reframe dong"
    state["resolved_language"] = "id"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "thought_record"
    payload = out["cbt_directive"]["payload"]
    assert "step" in payload
    assert "bot_prompt" in payload
    assert out["cbt_state"]["thought_record_active"] is True


@t("node thought record resume advances")
async def test_node_tr_resume():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "aku pasti gagal final, bantu reframe dong"
    state["resolved_language"] = "id"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    first_step = out["cbt_directive"]["payload"]["step"]
    out["current_message"] = "aku pasti gagal final besok"
    out2 = await dialogue_policy_node(out, audit=NullGuardrailLogger())
    assert out2["cbt_directive"]["payload"]["step"] != first_step


# LLM-judge router (hybrid path)


class _StubAIMessage:
    """Minimal stand-in for an AIMessage with a .content attribute."""

    def __init__(self, content: str) -> None:
        self.content = content


class _FakeJudgeLLM:
    """
    Fake LangChain-like client.

    Stores the prompts received so tests can assert the judge actually
    saw the expected context (KG distortions, last_directive, etc.).
    The response can be a static string or a callable that takes the
    list of messages and returns a string.
    """

    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[list[Any]] = []

    async def ainvoke(self, messages: list[Any]) -> _StubAIMessage:
        self.calls.append(messages)
        if callable(self._response):
            payload = self._response(messages)
        else:
            payload = self._response
        return _StubAIMessage(payload)


class _ExplodingLLM:
    """LLM that raises on ainvoke, used to test graceful fallback."""

    async def ainvoke(self, messages: list[Any]) -> _StubAIMessage:
        raise RuntimeError("simulated provider failure")


@t("judge parses valid JSON into outcome")
async def test_judge_parses_valid_json():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"distortion_active",'
        '"distortion":"catastrophizing","confidence":0.82,'
        '"rationale":"user catastrophizes about finals"}'
    )
    outcome = await judge_technique(
        _state(current_message="aku pasti gagal final"),
        llm=llm,
    )
    assert outcome is not None
    assert outcome.technique is CBTTechnique.REFRAME
    assert outcome.distortion == "catastrophizing"
    assert 0.0 <= outcome.confidence <= 1.0


@t("judge handles markdown fenced JSON")
async def test_judge_handles_fence():
    llm = _FakeJudgeLLM(
        "```json\n"
        '{"technique":"validate","reason":"default","distortion":null,'
        '"confidence":0.7,"rationale":"nothing alarming"}\n'
        "```"
    )
    outcome = await judge_technique(_state(current_message="halo"), llm=llm)
    assert outcome is not None
    assert outcome.technique is CBTTechnique.VALIDATE


@t("judge drops unknown technique to validate")
async def test_judge_unknown_technique_validates():
    llm = _FakeJudgeLLM(
        '{"technique":"meditation","reason":"foo","distortion":null,'
        '"confidence":0.9,"rationale":"x"}'
    )
    outcome = await judge_technique(_state(), llm=llm)
    assert outcome is not None
    assert outcome.technique is CBTTechnique.VALIDATE


@t("judge drops unknown distortion to None")
async def test_judge_unknown_distortion_none():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":"hallucination",'
        '"confidence":0.6,"rationale":"r"}'
    )
    outcome = await judge_technique(_state(), llm=llm)
    assert outcome is not None
    assert outcome.distortion is None


@t("judge returns None on non-json output")
async def test_judge_non_json_returns_none():
    llm = _FakeJudgeLLM("sorry I cannot comply")
    outcome = await judge_technique(_state(), llm=llm)
    assert outcome is None


@t("judge returns None on LLM exception")
async def test_judge_exception_returns_none():
    llm = _ExplodingLLM()
    outcome = await judge_technique(_state(), llm=llm)
    assert outcome is None


@t("judge prompt carries kg context and last directive")
async def test_judge_prompt_carries_context():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":null,'
        '"confidence":0.8,"rationale":"r"}'
    )
    state = _state(
        current_message="aku selalu salah",
        kg_context=(
            "[unchallenged cognitive distortions]\n"
            "- [overgeneralization] aku selalu gagal"
        ),
        cbt_state={
            "last_directive": {
                "technique": "validate",
                "reason": "default_validate",
                "payload": {},
            },
        },
    )
    await judge_technique(state, llm=llm)
    assert llm.calls, "judge should have invoked the LLM"
    rendered = llm.calls[0][1].content
    assert "[unchallenged cognitive distortions]" in rendered
    assert "technique=validate" in rendered


@t("route_with_llm safety blocks bypass judge")
async def test_route_with_llm_safety_bypasses_judge():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":null,'
        '"confidence":0.9,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(safety_flag="crisis"),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.NONE
    assert not llm.calls, "judge must not be called when safety blocks"


@t("route_with_llm phq9 active bypasses judge")
async def test_route_with_llm_phq9_bypasses_judge():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":null,'
        '"confidence":0.9,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(phq9_state={"phase": "in_progress"}),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.NONE
    assert not llm.calls


@t("route_with_llm acute distress bypasses judge")
async def test_route_with_llm_acute_bypasses_judge():
    # Acute-distress hard rule was removed (no per-turn PAD). Verify
    # the judge IS now consulted for affect-laden messages, since the
    # rule layer no longer gates acute affect.
    llm = _FakeJudgeLLM(
        '{"technique":"grounding","reason":"acute_text","distortion":null,'
        '"confidence":0.9,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(current_message="panik banget rasanya"),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.GROUNDING
    assert llm.calls, "judge SHOULD be consulted now that PAD rule is gone"


@t("route_with_llm in-progress thought record bypasses judge")
async def test_route_with_llm_tr_bypasses_judge():
    llm = _FakeJudgeLLM(
        '{"technique":"validate","reason":"x","distortion":null,'
        '"confidence":0.9,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(
            current_message="ok lanjut",
            cbt_state={"thought_record_active": True},
        ),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.THOUGHT_RECORD
    assert not llm.calls


@t("route_with_llm uses judge when no safety rule fires")
async def test_route_with_llm_uses_judge():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"distortion_active",'
        '"distortion":"catastrophizing","confidence":0.85,'
        '"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(current_message="aku pasti gagal final"),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.REFRAME
    assert d.payload.get("distortion") == "catastrophizing"
    assert "llm_judge" in d.signals


@t("route_with_llm low confidence falls back to rules")
async def test_route_with_llm_low_confidence_falls_back():
    # Judge returns low confidence; rule based route should win.
    llm = _FakeJudgeLLM(
        '{"technique":"behavior_activation","reason":"x",'
        '"distortion":null,"confidence":0.1,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(current_message="halo gimana hari ini"),
        judge_llm=llm,
    )
    # Rule based route() on neutral text returns validate.
    assert d.technique is CBTTechnique.VALIDATE
    assert "llm_judge" not in d.signals


@t("route_with_llm bad json falls back to rules")
async def test_route_with_llm_bad_json_falls_back():
    llm = _FakeJudgeLLM("not json at all")
    d = await route_with_llm(
        _state(current_message="aku selalu gagal"),
        judge_llm=llm,
    )
    # Falls back to rule based route -> reframe on distortion cue.
    assert d.technique is CBTTechnique.REFRAME


@t("route_with_llm exception falls back to rules")
async def test_route_with_llm_exception_falls_back():
    llm = _ExplodingLLM()
    d = await route_with_llm(
        _state(current_message="halo"),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.VALIDATE


@t("route_with_llm opt-out cooldown post-judge")
async def test_route_with_llm_cooldown():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":"catastrophizing",'
        '"confidence":0.85,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(
            current_message="aku pasti gagal",
            cbt_state={
                "last_offered": "reframe",
                "declined_last_offer": True,
            },
        ),
        judge_llm=llm,
    )
    assert d.technique is CBTTechnique.VALIDATE
    assert d.reason == "opt_out_cooldown"
    assert d.payload.get("deferred") == "reframe"


@t("dialogue policy node uses judge when provided")
async def test_node_uses_judge():
    llm = _FakeJudgeLLM(
        '{"technique":"self_compassion","reason":"x","distortion":null,'
        '"confidence":0.8,"rationale":"r"}'
    )
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "i feel like maybe today was tough"
    out = await dialogue_policy_node(
        state, audit=NullGuardrailLogger(), judge_llm=llm,
    )
    assert out["cbt_node_active"] == "self_compassion"
    assert llm.calls


@t("dialogue policy node without judge uses rules")
async def test_node_no_judge_uses_rules():
    state = empty_conversation_state(user_id="u1", session_id="s1")
    state["current_message"] = "halo, hari ini gimana"
    out = await dialogue_policy_node(state, audit=NullGuardrailLogger())
    assert out["cbt_node_active"] == "validate"


@t("judge surfaces kg distortion when judge returned none")
async def test_route_with_llm_uses_kg_distortion_signal():
    llm = _FakeJudgeLLM(
        '{"technique":"reframe","reason":"x","distortion":null,'
        '"confidence":0.85,"rationale":"r"}'
    )
    d = await route_with_llm(
        _state(current_message="aku selalu gagal"),
        judge_llm=llm,
    )
    # Sync signals layer extracts distortion from message; the judge
    # left it blank but the decision payload should still anchor on
    # the detected name.
    assert d.payload.get("distortion") == "overgeneralization"
    assert "kg_distortion" in d.signals



async def main():
    section("Distortion taxonomy")
    await test_registry()
    await test_detect()
    await test_detect_neutral()

    section("Router")
    await test_safety_flag()
    await test_phq9_active()
    await test_resume_tr()
    await test_distortion_reframe()
    await test_reframe_request_escalation()
    await test_avoidance_ba()
    await test_psychoed()
    await test_default()
    await test_optout()

    section("Thought record")
    await test_tr_full()
    await test_tr_persist()
    await test_tr_en()

    section("Dialogue policy node")
    await test_node_default()
    await test_node_reframe()
    await test_node_safety()
    await test_node_phq9()
    await test_node_decline_marks()
    await test_node_cooldown()
    await test_node_tr_start()
    await test_node_tr_resume()

    section("LLM-judge router (hybrid)")
    await test_judge_parses_valid_json()
    await test_judge_handles_fence()
    await test_judge_unknown_technique_validates()
    await test_judge_unknown_distortion_none()
    await test_judge_non_json_returns_none()
    await test_judge_exception_returns_none()
    await test_judge_prompt_carries_context()
    await test_route_with_llm_safety_bypasses_judge()
    await test_route_with_llm_phq9_bypasses_judge()
    await test_route_with_llm_acute_bypasses_judge()
    await test_route_with_llm_tr_bypasses_judge()
    await test_route_with_llm_uses_judge()
    await test_route_with_llm_low_confidence_falls_back()
    await test_route_with_llm_bad_json_falls_back()
    await test_route_with_llm_exception_falls_back()
    await test_route_with_llm_cooldown()
    await test_node_uses_judge()
    await test_node_no_judge_uses_rules()
    await test_route_with_llm_uses_kg_distortion_signal()

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

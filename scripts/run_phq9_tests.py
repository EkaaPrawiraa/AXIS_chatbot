"""
Standalone PHQ-9 test runner. Mirrors the pytest suite using only the
standard library so the smoke test runs even when pytest is not
installed. Each section prints a short pass/fail report.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/sessions/focused-dreamy-albattani/mnt/CompanionshipChatBot")
sys.path.insert(0, str(ROOT))

from agentic.agent.graph import (
    route_after_dialogue,
    route_after_output_guardrail as route_after_guardrail,
)
from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.nodes.phq9_delivery import (
    WARMUP_TURNS_BEFORE_OFFER,
    phq9_delivery_node,
)
from agentic.agent.state import empty_conversation_state, empty_phq9_state
from agentic.assessment.conversational_delivery import (
    build_clarification,
    build_feedback_message,
    build_greeting,
    build_item_prompt,
    build_offer,
    score_text_response,
)
from agentic.assessment.phq9 import (
    NUM_ITEMS,
    PHQ9Response,
    PHQ9Severity,
    ResponseSource,
    compute_severity,
    detect_language_lightweight,
    resolve_language,
    score_phq9,
    to_storage_payload,
)
from agentic.memory.assessment_repo import (
    AssessmentRetrySchedule,
    DistressSnapshot,
    LastPHQ9Snapshot,
)



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


# Fakes (mirror conftest)


class FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    def __init__(self, *, script=None, responder=None) -> None:
        self.script = list(script or [])
        self.responder = responder
        self.calls: list = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        if self.responder is not None:
            user_text = ""
            for m in messages:
                cls = m.__class__.__name__
                msg_type = getattr(m, "type", "")
                if "Human" in cls or msg_type == "human":
                    user_text = m.content
            return FakeAIMessage(self.responder(user_text))
        if not self.script:
            return FakeAIMessage('{"score": 0, "confidence": 1.0}')
        return FakeAIMessage(self.script.pop(0))


def keyword_responder(text: str) -> str:
    """
    Fake judge LLM. Looks at the user answer block (regardless of
    whether the prompt is from the legacy scorer template or the new
    judge template) and returns a JSON object compatible with both:

      legacy:  {"score": int, "confidence": float}
      judge:   {"score": int, "confidence": float, "action": str,
                "next_item": null, "rationale": ""}
    """
    import re

    # Match the new judge template first.
    m = re.search(r"User's latest reply:\s*\"\"\"\s*(.*?)\s*\"\"\"",
                  text, re.DOTALL)
    if not m:
        m = re.search(r'User answer:\s*"""\s*(.*?)\s*"""', text, re.DOTALL)
    answer = (m.group(1) if m else text).lower().strip()

    def _payload(score: int, conf: float, action: str = "advance") -> str:
        return json.dumps({
            "score": score, "confidence": conf, "action": action,
            "next_item": None, "rationale": "",
        })

    if "ambig" in answer:
        return _payload(1, 0.3, action="clarify")
    if "hampir setiap" in answer or "nearly every day" in answer:
        return _payload(3, 0.95)
    if "lebih dari setengah" in answer or "more than half" in answer:
        return _payload(2, 0.9)
    if "beberapa hari" in answer or "several days" in answer:
        return _payload(1, 0.9)
    if "tidak sama sekali" in answer or "not at all" in answer:
        return _payload(0, 0.95)
    if answer in {"0", "1", "2", "3"}:
        return _payload(int(answer), 0.99)
    return _payload(0, 0.85)


class FakeRepo:
    def __init__(self):
        self.last = None
        self.pending_retry = None
        self.distress = DistressSnapshot(0, None, False)
        self.saved_results = []
        self.cleared = []
        self.scheduled = []
        # In-flight PHQ-9 progress mock: keyed by (user_id, session_id).
        self.progress: dict[tuple[str, str], dict] = {}
        self.progress_saves: list[tuple[str, str]] = []
        self.progress_clears: list[tuple[str, str]] = []

    async def get_last_phq9(self, _):
        return self.last

    async def get_pending_retry(self, _):
        return self.pending_retry

    async def get_distress_snapshot(self, _):
        return self.distress

    async def save_phq9_result(self, r):
        self.saved_results.append(r)

    async def schedule_retry(self, *, user_id, days, reason):
        sched = AssessmentRetrySchedule(
            user_id=user_id,
            next_attempt_at=datetime.now(timezone.utc) + timedelta(days=days),
            reason=reason,
        )
        self.scheduled.append((user_id, days, reason))
        self.pending_retry = sched
        return sched

    async def clear_retry(self, user_id):
        self.cleared.append(user_id)
        self.pending_retry = None

    # PHQ-9 in-flight progress

    async def save_phq9_progress(self, *, user_id, session_id, state):
        # Deep-copy enough so downstream mutations don't leak into the
        # stored snapshot.
        responses = dict(state.get("responses") or {})
        self.progress[(user_id, session_id)] = {
            "phase": state.get("phase"),
            "active_item": state.get("active_item"),
            "responses": {int(k): dict(v) for k, v in responses.items()},
            "back_count": int(state.get("back_count") or 0),
            "tier": state.get("tier"),
            "language": state.get("language"),
            "user_initiated": bool(state.get("user_initiated") or False),
        }
        self.progress_saves.append((user_id, session_id))

    async def load_phq9_progress(self, *, user_id, session_id):
        row = self.progress.get((user_id, session_id))
        if row is None:
            return None
        return {
            "phase": row["phase"],
            "active_item": row["active_item"],
            "responses": {int(k): dict(v) for k, v in row["responses"].items()},
            "back_count": int(row["back_count"]),
            "tier": row["tier"],
            "language": row["language"],
            "user_initiated": row["user_initiated"],
        }

    async def clear_phq9_progress(self, *, user_id, session_id):
        self.progress.pop((user_id, session_id), None)
        self.progress_clears.append((user_id, session_id))


# Section 1: pure scoring


@t("severity boundaries")
def test_severity_bounds():
    cases = [
        (0, PHQ9Severity.MINIMAL), (4, PHQ9Severity.MINIMAL),
        (5, PHQ9Severity.MILD), (9, PHQ9Severity.MILD),
        (10, PHQ9Severity.MODERATE), (14, PHQ9Severity.MODERATE),
        (15, PHQ9Severity.MODERATELY_SEVERE), (19, PHQ9Severity.MODERATELY_SEVERE),
        (20, PHQ9Severity.SEVERE), (27, PHQ9Severity.SEVERE),
    ]
    for total, expected in cases:
        got = compute_severity(total)
        assert got is expected, f"{total} => {got}, want {expected}"


@t("severity rejects out of range")
def test_severity_oob():
    for bad in (-1, 28, 100):
        try:
            compute_severity(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad}")


@t("score_phq9 minimal all zeros")
def test_score_minimal():
    rs = [PHQ9Response(item_id=i, score=0, source=ResponseSource.BUTTON)
          for i in range(1, 10)]
    r = score_phq9(user_id="u", session_id="s", responses=rs, language="id")
    assert r.total_score == 0
    assert r.severity is PHQ9Severity.MINIMAL
    assert r.item9_flagged is False


@t("score_phq9 severe all threes")
def test_score_severe():
    rs = [PHQ9Response(item_id=i, score=3, source=ResponseSource.BUTTON)
          for i in range(1, 10)]
    r = score_phq9(user_id="u", session_id="s", responses=rs, language="id")
    assert r.total_score == 27
    assert r.severity is PHQ9Severity.SEVERE
    assert r.item9_flagged is True


@t("score_phq9 delta from previous")
def test_score_delta():
    rs = [PHQ9Response(item_id=i, score=2, source=ResponseSource.BUTTON)
          for i in range(1, 10)]
    r = score_phq9(user_id="u", session_id="s", responses=rs,
                   language="id", previous_total=10)
    assert r.total_score == 18
    assert r.delta_from_previous == 8


@t("score_phq9 missing items raises")
def test_score_missing():
    rs = [PHQ9Response(item_id=i, score=0, source=ResponseSource.BUTTON)
          for i in range(1, 9)]  # 8 items
    try:
        score_phq9(user_id="u", session_id="s", responses=rs, language="id")
    except ValueError as e:
        assert "missing" in str(e)
        return
    raise AssertionError("expected ValueError")


@t("score_phq9 duplicate item raises")
def test_score_dup():
    rs = [PHQ9Response(item_id=i, score=0, source=ResponseSource.BUTTON)
          for i in range(1, 10)]
    rs.append(rs[0])
    try:
        score_phq9(user_id="u", session_id="s", responses=rs, language="id")
    except ValueError as e:
        assert "duplicate" in str(e)
        return
    raise AssertionError("expected ValueError")


@t("score_phq9 item9 only flag")
def test_score_item9_only():
    scores = [0] * 9
    scores[8] = 1
    rs = [PHQ9Response(item_id=i + 1, score=scores[i],
                       source=ResponseSource.BUTTON) for i in range(9)]
    r = score_phq9(user_id="u", session_id="s", responses=rs, language="en")
    assert r.item9_flagged is True
    assert r.total_score == 1


@t("storage payload shape")
def test_storage_payload():
    rs = [PHQ9Response(item_id=i, score=2, source=ResponseSource.BUTTON)
          for i in range(1, 10)]
    r = score_phq9(user_id="u", session_id="s", responses=rs,
                   language="id", previous_total=10)
    payload = to_storage_payload(r)
    assert payload["instrument"] == "PHQ-9"
    assert payload["score"] == 18.0
    assert payload["delta_from_prev"] == 8.0
    assert payload["item_responses"] == {str(i): 2 for i in range(1, 10)}


# Section 2: language detection


@t("detect lightweight id")
def test_detect_id():
    assert detect_language_lightweight("saya merasa sangat lelah") == "id"


@t("detect lightweight en")
def test_detect_en():
    assert detect_language_lightweight("I am tired and sad") == "en"


@t("resolve prefers user pref")
def test_resolve_pref():
    assert resolve_language(user_pref="en",
                            recent_messages=["saya sedih"]) == "en"


@t("resolve falls back to detection")
def test_resolve_detect():
    assert resolve_language(user_pref=None,
                            recent_messages=["saya capek banget"]) == "id"


# Section 3: prompt builders


@t("greeting id has phq-9 ref")
def test_greeting_id():
    assert "PHQ-9" in build_greeting("id")


@t("offer id contains ngecek or ngobrol")
def test_offer_id():
    text = build_offer("id")
    assert "ngecek" in text or "ngobrol" in text


@t("item prompt 1..9 includes all four options")
def test_item_prompts_all_options():
    for i in range(1, NUM_ITEMS + 1):
        prompt = build_item_prompt(i, "id")
        for s in range(4):
            assert f"{s}." in prompt, f"item {i} missing option {s}"


@t("clarification mentions item id")
def test_clarification_mentions():
    assert "5" in build_clarification(5, "id", "kadang aja")


# Section 4: text scorer


@t("text scorer high confidence button match")
async def test_scorer_high_conf():
    llm = FakeLLM(responder=keyword_responder)
    out = await score_text_response(
        item_id=1, user_text="hampir setiap hari", language="id", llm=llm,
    )
    assert out.score == 3
    assert out.needs_clarification is False


@t("text scorer low confidence triggers clarification")
async def test_scorer_low_conf():
    llm = FakeLLM(responder=keyword_responder)
    out = await score_text_response(
        item_id=1, user_text="ambig answer", language="id", llm=llm,
    )
    assert out.needs_clarification is True


@t("text scorer malformed json falls back")
async def test_scorer_malformed():
    llm = FakeLLM(script=["this is not json"])
    out = await score_text_response(
        item_id=2, user_text="hello", language="en", llm=llm,
    )
    assert out.score == 0
    assert out.needs_clarification is True


@t("text scorer broken llm flagged")
async def test_scorer_broken():
    class Broken:
        async def ainvoke(self, _):
            raise RuntimeError("boom")
    out = await score_text_response(
        item_id=2, user_text="hello", language="en", llm=Broken(),
    )
    assert out.needs_clarification is True


# Section 5: trigger node (Tier 1 + Tier 2)


def _check_state(**kw):
    state = empty_conversation_state(
        user_id=kw.get("user_id", "u1"),
        session_id="s1",
        language_pref=kw.get("language_pref"),
    )
    state["session_turn"] = kw.get("session_turn", 0)
    state["current_message"] = kw.get("user_message", "")
    state["messages"] = kw.get("history", [])
    return state


@t("tier1 first time user offer pending")
async def test_tier1_first_time():
    repo = FakeRepo()
    state = _check_state(user_message="halo capek")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "offer_pending"
    assert out["phq9_state"]["tier"] == "scheduled"


@t("tier1 recent admin no trigger")
async def test_tier1_recent():
    repo = FakeRepo()
    repo.last = LastPHQ9Snapshot(
        administered_at=datetime.now(timezone.utc) - timedelta(days=3),
        total_score=8, severity=PHQ9Severity.MILD, item_scores=(1,) * 9,
    )
    state = _check_state(user_message="halo")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "idle"


@t("tier1 acute distress (KG aggregate) suppresses + retry 3 days")
async def test_tier1_acute():
    repo = FakeRepo()
    # Drive acute via KG snapshot (per-turn PAD was removed).
    repo.distress = DistressSnapshot(0, -0.8, False)
    state = _check_state(user_message="aku ga sanggup")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["reason"] == "suppressed:acute_distress"
    _, days, reason = repo.scheduled[-1]
    assert days == 3
    assert reason == "acute_distress"


@t("tier1 recent severe triggers 7 day cool-down")
async def test_tier1_severe_cool():
    repo = FakeRepo()
    repo.last = LastPHQ9Snapshot(
        administered_at=datetime.now(timezone.utc) - timedelta(days=20),
        total_score=22, severity=PHQ9Severity.SEVERE, item_scores=(2,) * 9,
    )
    state = _check_state(user_message="halo")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["reason"] == "suppressed:recent_worsening"
    _, days, reason = repo.scheduled[-1]
    assert days == 7
    assert reason == "recent_worsening"


@t("tier2 high distress count triggers offer")
async def test_tier2_count():
    repo = FakeRepo()
    repo.last = LastPHQ9Snapshot(
        administered_at=datetime.now(timezone.utc) - timedelta(days=2),
        total_score=8, severity=PHQ9Severity.MILD, item_scores=(1,) * 9,
    )
    repo.distress = DistressSnapshot(3, -0.3, False)
    state = _check_state(user_message="capek banget")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "offer_pending"
    assert out["phq9_state"]["tier"] == "event"


@t("tier2 recurring trigger active triggers offer")
async def test_tier2_recurring():
    repo = FakeRepo()
    repo.last = LastPHQ9Snapshot(
        administered_at=datetime.now(timezone.utc) - timedelta(days=1),
        total_score=4, severity=PHQ9Severity.MINIMAL, item_scores=(0,) * 9,
    )
    repo.distress = DistressSnapshot(0, -0.2, True)
    state = _check_state(user_message="ketemu mantan")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "offer_pending"


@t("tier2 acute distress (KG aggregate) overrides cluster and suppresses")
async def test_tier2_acute_override():
    repo = FakeRepo()
    repo.last = LastPHQ9Snapshot(
        administered_at=datetime.now(timezone.utc) - timedelta(days=1),
        total_score=4, severity=PHQ9Severity.MINIMAL, item_scores=(0,) * 9,
    )
    # KG snapshot drives acute since per-turn PAD is gone.
    repo.distress = DistressSnapshot(3, -0.8, False)
    state = _check_state(user_message="ga kuat")
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "idle"
    assert out["phq9_state"]["reason"] == "suppressed:event_acute_distress"


@t("idempotent when already in_progress")
async def test_idempotent():
    repo = FakeRepo()
    state = _check_state(user_message="halo")
    state["phq9_state"] = empty_phq9_state()
    state["phq9_state"]["phase"] = "in_progress"
    state["phq9_state"]["active_item"] = 4
    out = await phq9_check_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "in_progress"
    assert out["phq9_state"]["active_item"] == 4


# Section 6: delivery state machine


def _delivery_state(*, phase="offer_pending", tier="scheduled",
                    session_turn=WARMUP_TURNS_BEFORE_OFFER,
                    user_message="", language="id"):
    state = empty_conversation_state(
        user_id="u1", session_id="s1", language_pref=language,
    )
    state["session_turn"] = session_turn
    state["current_message"] = user_message
    state["resolved_language"] = language
    phq9 = empty_phq9_state()
    phq9["phase"] = phase
    phq9["tier"] = tier
    phq9["language"] = language
    state["phq9_state"] = phq9
    return state


@t("delivery warm-up holds offer")
async def test_delivery_warmup_hold():
    repo = FakeRepo()
    state = _delivery_state(session_turn=0)
    out = await phq9_delivery_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "offer_pending"
    assert not out.get("response_draft")


@t("delivery offer arms response_generator after warm-up")
async def test_delivery_offer_speak():
    # Phase 2 contract: subgraph offer node no longer emits a static
    # invitation. It only sets ``offer_armed`` so the
    # response_generator can weave the invite contextually. Phase
    # remains ``offer_pending`` until the response_generator runs.
    repo = FakeRepo()
    state = _delivery_state(session_turn=WARMUP_TURNS_BEFORE_OFFER)
    out = await phq9_delivery_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "offer_pending"
    assert out["phq9_state"].get("offer_armed") is True
    # No response_draft is set by the subgraph in this turn.
    assert not out.get("response_draft")


@t("delivery decline acknowledged")
async def test_delivery_decline():
    repo = FakeRepo()
    state = _delivery_state(phase="offered", user_message="nanti aja")
    out = await phq9_delivery_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "declined"


@t("delivery accept starts questionnaire")
async def test_delivery_accept():
    repo = FakeRepo()
    state = _delivery_state(phase="offered", user_message="iya boleh")
    out = await phq9_delivery_node(state, repo=repo)
    assert out["phq9_state"]["phase"] == "in_progress"
    assert out["phq9_state"]["active_item"] == 1
    assert "Pertanyaan 1" in out["response_draft"]


@t("delivery button tap advances")
async def test_delivery_button_advance():
    repo = FakeRepo()
    state = _delivery_state(phase="in_progress", user_message="2")
    state["phq9_state"]["active_item"] = 1
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=FakeLLM(responder=keyword_responder),
    )
    assert out["phq9_state"]["active_item"] == 2
    assert out["phq9_state"]["responses"][1]["score"] == 2
    # Subgraph routes every reply through the LLM judge; the legacy
    # regex-based "button" source is gone.
    assert out["phq9_state"]["responses"][1]["source"] == "text_llm"


@t("delivery text answer uses llm scorer")
async def test_delivery_text():
    # Use natural-language phrasing that does not match a label
    # exactly so the button parser falls through to the LLM scorer.
    repo = FakeRepo()
    state = _delivery_state(
        phase="in_progress",
        user_message="iya, hampir setiap hari banget",
    )
    state["phq9_state"]["active_item"] = 1
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=FakeLLM(responder=keyword_responder),
    )
    assert out["phq9_state"]["responses"][1]["source"] == "text_llm"
    assert out["phq9_state"]["responses"][1]["score"] == 3


@t("delivery low confidence triggers clarification")
async def test_delivery_low_conf():
    repo = FakeRepo()
    state = _delivery_state(phase="in_progress", user_message="ambig answer")
    state["phq9_state"]["active_item"] = 4
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=FakeLLM(responder=keyword_responder),
    )
    assert out["phq9_state"]["phase"] == "awaiting_clar"
    assert out["phq9_state"]["active_item"] == 4


@t("delivery full run all 1s persists and flags")
async def test_delivery_full_run_ones():
    repo = FakeRepo()
    feedback = FakeLLM(script=["Skor PHQ-9 kamu menunjukkan gejala ringan."])
    state = _delivery_state(phase="in_progress")
    state["phq9_state"]["active_item"] = 1
    for item_id in range(1, NUM_ITEMS + 1):
        state["current_message"] = "1"
        state["phq9_state"]["active_item"] = item_id
        state = await phq9_delivery_node(
            state, repo=repo,
            judge_llm=FakeLLM(responder=keyword_responder),
            feedback_llm=feedback,
        )
    phq9 = state["phq9_state"]
    # Item 9 == 1 flags safety, so phase ends in deferred_crisis
    # rather than completed. The graph routes through crisis_guardrail
    # before session_end based on route_to_crisis_after.
    assert phq9["phase"] == "deferred_crisis"
    assert phq9["last_total"] == 9
    assert phq9["last_severity"] == "mild"
    assert phq9["item9_flagged"] is True
    assert phq9["route_to_crisis_after"] is True
    assert state["safety_flag"] == "escalate"
    assert len(repo.saved_results) == 1
    assert repo.cleared == ["u1"]


@t("delivery full run all 0s no crisis route")
async def test_delivery_full_run_zeros():
    repo = FakeRepo()
    feedback = FakeLLM(script=["Skor PHQ-9 kamu adalah 0 (minimal)."])
    state = _delivery_state(phase="in_progress")
    for item_id in range(1, NUM_ITEMS + 1):
        state["current_message"] = "0"
        state["phq9_state"]["active_item"] = item_id
        state = await phq9_delivery_node(
            state, repo=repo,
            judge_llm=FakeLLM(responder=keyword_responder),
            feedback_llm=feedback,
        )
    phq9 = state["phq9_state"]
    assert phq9["phase"] == "completed"
    assert phq9["item9_flagged"] is False
    assert phq9["route_to_crisis_after"] is False
    assert state.get("safety_flag") != "escalate"


# Section 6.5: subgraph specific behaviors


def _subgraph_state(*, active_item: int, language: str = "id"):
    state = empty_conversation_state(user_id="u1", session_id="s1")
    phq9 = empty_phq9_state()
    phq9["phase"] = "in_progress"
    phq9["language"] = language
    phq9["active_item"] = active_item
    state["phq9_state"] = phq9
    state["resolved_language"] = language
    return state


def _judge_responder(action: str, score: int = 1, next_item=None):
    """Return a fake LLM whose ainvoke yields a fixed judge JSON."""

    payload = json.dumps({
        "score": score, "confidence": 0.9, "action": action,
        "next_item": next_item, "rationale": "",
    })

    class _R:
        async def ainvoke(self, _):
            return FakeAIMessage(payload)
    return _R()


@t("subgraph judge clarify keeps active_item")
async def test_subgraph_clarify():
    repo = FakeRepo()
    state = _subgraph_state(active_item=3)
    state["current_message"] = "kayak gitu deh"
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=_judge_responder("clarify"),
    )
    assert out["phq9_state"]["phase"] == "awaiting_clar"
    assert out["phq9_state"]["active_item"] == 3
    assert out["phq9_state"]["awaiting_clarification"] is True


@t("subgraph back navigation moves pointer back")
async def test_subgraph_back():
    repo = FakeRepo()
    state = _subgraph_state(active_item=5)
    state["current_message"] = "boleh balik ke yang tadi"
    out = await phq9_delivery_node(
        state, repo=repo,
        judge_llm=_judge_responder("back", next_item=3),
    )
    assert out["phq9_state"]["active_item"] == 3
    assert out["phq9_state"]["back_count"] == 1


@t("subgraph back budget caps at MAX_BACK_NAVIGATIONS")
async def test_subgraph_back_budget():
    from agentic.agent.phq9.subgraph import MAX_BACK_NAVIGATIONS

    repo = FakeRepo()
    state = _subgraph_state(active_item=5)
    state["phq9_state"]["back_count"] = MAX_BACK_NAVIGATIONS
    state["current_message"] = "balik dong"
    out = await phq9_delivery_node(
        state, repo=repo,
        judge_llm=_judge_responder("back", next_item=2),
    )
    # Cap reached: demoted to clarify on the same item.
    assert out["phq9_state"]["phase"] == "awaiting_clar"
    assert out["phq9_state"]["active_item"] == 5


@t("subgraph item 9 forces advance even if judge says back")
async def test_subgraph_item9_lock():
    repo = FakeRepo()
    state = _subgraph_state(active_item=9)
    # Pre-fill items 1..8 so finalize completes after the forced
    # advance.
    state["phq9_state"]["responses"] = {
        i: {"score": 0, "source": "text_llm", "raw_text": "0", "confidence": 0.9}
        for i in range(1, 9)
    }
    state["current_message"] = "kadang"
    out = await phq9_delivery_node(
        state, repo=repo,
        judge_llm=_judge_responder("back", score=1, next_item=8),
        feedback_llm=FakeLLM(script=["feedback"]),
    )
    # Item 9 must finalize (deferred_crisis since score 1 flags item9).
    assert out["phq9_state"]["phase"] == "deferred_crisis"
    assert out["phq9_state"]["item9_flagged"] is True
    assert out["phq9_state"]["route_to_crisis_after"] is True


@t("subgraph judge stop sets safety_flag crisis")
async def test_subgraph_stop():
    repo = FakeRepo()
    state = _subgraph_state(active_item=4)
    state["current_message"] = "ga kuat lagi"
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=_judge_responder("stop"),
    )
    assert out.get("safety_flag") == "crisis"


@t("subgraph judge decline ends with declined phase")
async def test_subgraph_judge_decline():
    repo = FakeRepo()
    state = _subgraph_state(active_item=2)
    state["current_message"] = "udahan aja deh"
    out = await phq9_delivery_node(
        state, repo=repo, judge_llm=_judge_responder("decline"),
    )
    assert out["phq9_state"]["phase"] == "declined"


# Section 7: graph routing


@t("route_after_dialogue active phases")
def test_route_dialogue_active():
    # Phase 2: offer_pending routes to response_generator (the
    # contextual offer overlay handles the invitation). Only the
    # explicit accept/decline + administration phases route to
    # phq9_delivery.
    for phase in ("offered", "in_progress", "awaiting_clar"):
        ph = empty_phq9_state()
        ph["phase"] = phase
        state = {"phq9_state": ph, "session_turn": 5}
        assert route_after_dialogue(state) == "phq9_delivery"


@t("route_after_dialogue offer_pending always goes to response_generator")
def test_route_dialogue_offer_pending_warmup():
    ph = empty_phq9_state()
    ph["phase"] = "offer_pending"
    # Warm-up not yet met
    state_a = {"phq9_state": ph, "session_turn": 0}
    assert route_after_dialogue(state_a) == "response_generator"
    # Past warm-up still routes to response_generator (contextual offer)
    state_b = {"phq9_state": ph, "session_turn": 5}
    assert route_after_dialogue(state_b) == "response_generator"


@t("route_after_dialogue terminal phases")
def test_route_dialogue_terminal():
    for phase in ("idle", "completed", "declined", "deferred_crisis"):
        ph = empty_phq9_state()
        ph["phase"] = phase
        assert route_after_dialogue({"phq9_state": ph}) == "response_generator"


@t("route_after_guardrail flags crisis")
def test_route_guard_flag():
    ph = empty_phq9_state()
    ph["route_to_crisis_after"] = True
    assert route_after_guardrail({"phq9_state": ph}) == "crisis_escalation"


@t("route_after_guardrail clears to session_end")
def test_route_guard_clear():
    ph = empty_phq9_state()
    ph["route_to_crisis_after"] = False
    assert route_after_guardrail({"phq9_state": ph}) == "session_end"


# Section 8: Explanation requests + score persistence


from agentic.agent.audit.guardrail_events import NullGuardrailLogger
from agentic.agent.phq9 import subgraph as _phq9_sg


class _StubAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeJudgeAlwaysAdvance:
    """Judge fake that records calls; default action ADVANCE score 0."""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return _StubAIMessage(
            '{"score":0,"confidence":0.95,"action":"advance",'
            '"next_item":null,"rationale":"ok"}'
        )


class _FakeClarificationLLM:
    """Clarification fake: returns a fixed natural explanation."""

    def __init__(self, text: str):
        self.text = text
        self.calls = []

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return _StubAIMessage(self.text)


def _engaged_state(*, item_id: int, user_message: str):
    """Build a ConversationState already mid-PHQ9 on the given item."""
    state = empty_conversation_state(
        user_id="user-clarif", session_id="sess-clarif", language_pref="id",
    )
    state["current_message"] = user_message
    state["resolved_language"] = "id"
    phq9 = empty_phq9_state()
    phq9["phase"] = "in_progress"
    phq9["tier"] = "scheduled"
    phq9["language"] = "id"
    phq9["active_item"] = item_id
    state["phq9_state"] = phq9
    return state


# Cue coverage: each line below maps a real user phrase to whether
# the detector should fire. Cited justifications:
#   * "jelasin dong" - Jakarta colloquial -in suffix, Sneddon ch.4
#   * "maksudnya gimana" - colloquial inverted clause
#   * "ga ngerti" - negation particle + comprehension verb
#   * "bingung" - bare adjective signaling confusion
#   * "contoh dong" - explicit example request
#   * "what does this mean" - English minimal
_CUE_CASES = [
    ("jelasin dong maksudnya", True),
    ("maksudnya gimana sih", True),
    ("ga ngerti pertanyaannya", True),
    ("gak paham", True),
    ("bingung deh", True),
    ("contoh dong", True),
    ("apa artinya pertanyaan ini", True),
    ("bisa diperjelas?", True),
    ("what does this mean", True),
    ("i don't understand", True),
    ("give me an example", True),
    # negative controls
    ("beberapa hari kayaknya", False),
    ("hampir setiap hari", False),
    ("tidak sama sekali", False),
    ("3", False),
]


@t("cue detector positive and negative cases")
def test_cue_detector_table():
    for phrase, expected in _CUE_CASES:
        got = _phq9_sg._is_explanation_request(phrase, "id")
        assert got is expected, f"{phrase!r}: got {got}, want {expected}"


@t("explanation request short-circuits judge")
async def test_explanation_short_circuits_judge():
    state = _engaged_state(item_id=1, user_message="jelasin dong maksudnya")
    judge = _FakeJudgeAlwaysAdvance()
    clarif = _FakeClarificationLLM("Pertanyaan ini ngecek minat kamu dalam 2 minggu terakhir.")

    out = await _phq9_sg._node_item(
        state,
        audit=NullGuardrailLogger(),
        judge_llm=judge,
        clarification_llm=clarif,
        repo=FakeRepo(),
        feedback_llm=None,
    )

    assert not judge.calls, "judge MUST NOT be called for explanation requests"
    assert clarif.calls, "clarification LLM should be called"
    assert out["phq9_state"]["phase"] == "awaiting_clar"
    assert out["phq9_state"]["awaiting_clarification"] is True
    # Score must not be added.
    assert int(out["phq9_state"].get("active_item") or 0) == 1
    assert out["phq9_state"].get("responses", {}).get(1) is None
    # LLM text was used directly.
    assert "minat kamu" in (out.get("response_draft") or "")


@t("explanation request persists progress with no score added")
async def test_explanation_persists_progress():
    state = _engaged_state(item_id=4, user_message="ga ngerti pertanyaannya")
    judge = _FakeJudgeAlwaysAdvance()
    clarif = _FakeClarificationLLM("Penjelasan singkat.")
    repo = FakeRepo()

    await _phq9_sg._node_item(
        state,
        audit=NullGuardrailLogger(),
        judge_llm=judge,
        clarification_llm=clarif,
        repo=repo,
        feedback_llm=None,
    )

    # Persistence is opportunistic but should have been called.
    saved = repo.progress.get(("user-clarif", "sess-clarif"))
    assert saved is not None, "save_phq9_progress should fire"
    assert saved["active_item"] == 4
    assert saved["responses"] == {}, "no score should be persisted"


@t("regular ambiguous answer still hits judge clarify path")
async def test_ambiguous_answer_uses_judge():
    state = _engaged_state(item_id=2, user_message="lumayan deh kayaknya")
    judge_replies = iter([
        '{"score":0,"confidence":0.2,"action":"clarify",'
        '"next_item":null,"rationale":"ambiguous"}',
    ])

    class _Judge:
        def __init__(self):
            self.calls = []

        async def ainvoke(self, messages):
            self.calls.append(messages)
            return _StubAIMessage(next(judge_replies))

    judge = _Judge()
    clarif = _FakeClarificationLLM("should not be called")
    out = await _phq9_sg._node_item(
        state,
        audit=NullGuardrailLogger(),
        judge_llm=judge,
        clarification_llm=clarif,
        repo=FakeRepo(),
        feedback_llm=None,
    )
    # Judge was consulted.
    assert judge.calls
    # Clarification LLM should NOT be called (no explanation request).
    assert not clarif.calls
    assert out["phq9_state"]["phase"] == "awaiting_clar"
    # The static re-prompt should be present.
    assert "lebih cocok" in (out.get("response_draft") or "").lower() \
        or "fits better" in (out.get("response_draft") or "").lower()


@t("save / load / clear progress roundtrip on fake repo")
async def test_progress_repo_roundtrip():
    repo = FakeRepo()
    state = {
        "phase": "in_progress",
        "active_item": 3,
        "responses": {1: {"score": 1, "source": "text_llm",
                          "raw_text": "kadang", "confidence": 0.7},
                      2: {"score": 0, "source": "text_llm",
                          "raw_text": "engga", "confidence": 0.9}},
        "back_count": 0,
        "tier": "scheduled",
        "language": "id",
        "user_initiated": False,
    }
    await repo.save_phq9_progress(
        user_id="u1", session_id="s1", state=state,
    )
    got = await repo.load_phq9_progress(user_id="u1", session_id="s1")
    assert got is not None
    assert got["active_item"] == 3
    assert set(got["responses"].keys()) == {1, 2}
    await repo.clear_phq9_progress(user_id="u1", session_id="s1")
    assert await repo.load_phq9_progress(user_id="u1", session_id="s1") is None


@t("rehydrate prefers persisted state on mismatch")
async def test_rehydration_prefers_persisted():
    from agentic.agent.nodes.phq9_check import phq9_check_node

    repo = FakeRepo()
    # Persisted: real progress with active_item=5 and 4 scored answers.
    await repo.save_phq9_progress(
        user_id="u-rh", session_id="s-rh",
        state={
            "phase": "in_progress",
            "active_item": 5,
            "responses": {
                i: {"score": 1, "source": "text_llm",
                    "raw_text": "x", "confidence": 0.8}
                for i in (1, 2, 3, 4)
            },
            "back_count": 0,
            "tier": "scheduled",
            "language": "id",
            "user_initiated": False,
        },
    )
    # Request claims active_item=2 (caller-side state went stale).
    state = empty_conversation_state(
        user_id="u-rh", session_id="s-rh", language_pref="id",
    )
    state["current_message"] = "kadang"
    phq9 = empty_phq9_state()
    phq9["phase"] = "in_progress"
    phq9["active_item"] = 2
    phq9["language"] = "id"
    state["phq9_state"] = phq9

    out = await phq9_check_node(state, repo=repo)

    # Server wins: active_item is 5 with 4 stored responses.
    assert out["phq9_state"]["active_item"] == 5
    assert set(out["phq9_state"]["responses"].keys()) == {1, 2, 3, 4}


@t("decline clears progress row")
async def test_decline_clears_progress():
    state = _engaged_state(item_id=3, user_message="ga deh, skip aja")
    state["phq9_state"]["responses"] = {
        1: {"score": 0, "source": "text_llm", "raw_text": "no", "confidence": 0.9},
    }
    repo = FakeRepo()

    class _DeclineJudge:
        async def ainvoke(self, messages):
            return _StubAIMessage(
                '{"score":0,"confidence":0.95,"action":"decline",'
                '"next_item":null,"rationale":"user opted out"}'
            )

    out = await _phq9_sg._node_item(
        state,
        audit=NullGuardrailLogger(),
        judge_llm=_DeclineJudge(),
        clarification_llm=None,
        repo=repo,
        feedback_llm=None,
    )

    assert out["phq9_state"]["phase"] == "declined"
    assert ("user-clarif", "sess-clarif") in repo.progress_clears



async def main():
    section("1. Pure scoring")
    await test_severity_bounds()
    await test_severity_oob()
    await test_score_minimal()
    await test_score_severe()
    await test_score_delta()
    await test_score_missing()
    await test_score_dup()
    await test_score_item9_only()
    await test_storage_payload()

    section("2. Language detection")
    await test_detect_id()
    await test_detect_en()
    await test_resolve_pref()
    await test_resolve_detect()

    section("3. Prompt builders")
    await test_greeting_id()
    await test_offer_id()
    await test_item_prompts_all_options()
    await test_clarification_mentions()

    section("4. Text scorer (mocked LLM)")
    await test_scorer_high_conf()
    await test_scorer_low_conf()
    await test_scorer_malformed()
    await test_scorer_broken()

    section("5. Trigger node")
    await test_tier1_first_time()
    await test_tier1_recent()
    await test_tier1_acute()
    await test_tier1_severe_cool()
    await test_tier2_count()
    await test_tier2_recurring()
    await test_tier2_acute_override()
    await test_idempotent()

    section("6. Delivery state machine")
    await test_delivery_warmup_hold()
    await test_delivery_offer_speak()
    await test_delivery_decline()
    await test_delivery_accept()
    await test_delivery_button_advance()
    await test_delivery_text()
    await test_delivery_low_conf()
    await test_delivery_full_run_ones()
    await test_delivery_full_run_zeros()

    section("6.5 Subgraph specific")
    await test_subgraph_clarify()
    await test_subgraph_back()
    await test_subgraph_back_budget()
    await test_subgraph_item9_lock()
    await test_subgraph_stop()
    await test_subgraph_judge_decline()

    section("7. Graph routing")
    await test_route_dialogue_active()
    await test_route_dialogue_offer_pending_warmup()
    await test_route_dialogue_terminal()
    await test_route_guard_flag()
    await test_route_guard_clear()

    section("8. Explanation + progress persistence")
    await test_cue_detector_table()
    await test_explanation_short_circuits_judge()
    await test_explanation_persists_progress()
    await test_ambiguous_answer_uses_judge()
    await test_progress_repo_roundtrip()
    await test_rehydration_prefers_persisted()
    await test_decline_clears_progress()

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

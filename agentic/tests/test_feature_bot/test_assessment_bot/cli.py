"""Assessment CLI bot (feature harness)."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.nodes.phq9_delivery import phq9_delivery_node
from agentic.agent.state import ConversationState, empty_conversation_state, empty_phq9_state
from agentic.assessment.phq9 import NUM_ITEMS, options_with_scores


# In-memory fakes (repo + LLM)


@dataclass
class _PendingRetry:
    next_attempt_at: datetime
    reason: str


@dataclass
class _LastPhq9:
    administered_at: datetime
    total_score: int
    severity: Any
    item_scores: tuple[int, ...]


@dataclass
class _DistressSnapshot:
    high_distress_session_count_7d: int = 0
    avg_emotion_valence_7d: float | None = None
    recurring_trigger_active: bool = False


class InMemoryAssessmentRepository:
    """Implements the small subset of AssessmentRepository needed by PHQ-9 nodes."""

    def __init__(self) -> None:
        self.last: _LastPhq9 | None = None
        self.pending_retry: _PendingRetry | None = None
        self.distress: _DistressSnapshot = _DistressSnapshot()
        self.saved_results: list[Any] = []
        self.cleared_retries_for: list[str] = []

    async def get_last_phq9(self, _user_id: str) -> _LastPhq9 | None:
        return self.last

    async def get_pending_retry(self, _user_id: str) -> Any | None:
        if self.pending_retry is None:
            return None

        class _Schedule:
            def __init__(self, next_attempt_at: datetime, reason: str) -> None:
                self.next_attempt_at = next_attempt_at
                self.reason = reason

        return _Schedule(self.pending_retry.next_attempt_at, self.pending_retry.reason)

    async def get_distress_snapshot(self, _user_id: str) -> _DistressSnapshot:
        return self.distress

    async def schedule_retry(self, *, user_id: str, days: int, reason: str) -> Any:
        # Keep next_attempt_at "now" for simplicity; the node only checks
        # whether it is in the future.
        self.pending_retry = _PendingRetry(next_attempt_at=datetime.now(timezone.utc), reason=reason)

        class _Schedule:
            def __init__(self, user_id: str, next_attempt_at: datetime, reason: str) -> None:
                self.user_id = user_id
                self.next_attempt_at = next_attempt_at
                self.reason = reason

        return _Schedule(user_id, self.pending_retry.next_attempt_at, self.pending_retry.reason)

    async def save_phq9_result(self, result: Any) -> None:
        self.saved_results.append(result)

    async def clear_retry(self, user_id: str) -> None:
        self.pending_retry = None
        self.cleared_retries_for.append(user_id)


class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    """Tiny stand-in for LangChain chat models (only .ainvoke is used)."""

    def __init__(self, responder) -> None:
        self._responder = responder
        self.calls: list[list[Any]] = []

    async def ainvoke(self, messages: list[Any]) -> _FakeAIMessage:
        self.calls.append(messages)
        # conversational_delivery sends [SystemMessage, HumanMessage]
        human = None
        for m in reversed(messages):
            if m.__class__.__name__ == "HumanMessage" or getattr(m, "type", None) == "human":
                human = m
                break
        user_prompt = getattr(human, "content", "") if human is not None else ""
        return _FakeAIMessage(self._responder(user_prompt))


_USER_ANSWER_RE = re.compile(r"User answer:\n\"\"\"\n(.*?)\n\"\"\"", re.DOTALL)


def _extract_user_answer_from_prompt(prompt: str) -> str:
    """Best-effort extraction of the user answer from the scorer template."""
    if not prompt:
        return ""
    m = _USER_ANSWER_RE.search(prompt)
    if m:
        return (m.group(1) or "").strip()
    # Fallback: if template changes, just use full prompt.
    return prompt.strip()


def build_fake_scorer_llm() -> FakeLLM:
    def respond(user_prompt: str) -> str:
        answer = _extract_user_answer_from_prompt(user_prompt).lower()
        # Low confidence path for clarification testing.
        if "ambig" in answer:
            return json.dumps({"score": 1, "confidence": 0.3})
        # Simple multilingual heuristics.
        if "hampir setiap" in answer or "nearly every" in answer:
            return json.dumps({"score": 3, "confidence": 0.95})
        if "lebih dari setengah" in answer or "more than half" in answer:
            return json.dumps({"score": 2, "confidence": 0.9})
        if "beberapa hari" in answer or "several days" in answer:
            return json.dumps({"score": 1, "confidence": 0.9})
        if "tidak sama sekali" in answer or "not at all" in answer:
            return json.dumps({"score": 0, "confidence": 0.95})
        # Generic default: medium confidence.
        return json.dumps({"score": 0, "confidence": 0.6})

    return FakeLLM(responder=respond)


def build_fake_feedback_llm(language: str) -> FakeLLM:
    def respond(_user_prompt: str) -> str:
        if language == "en":
            return "Thanks for answering. I saved your PHQ-9 result."
        return "Terima kasih sudah menjawab. Hasil PHQ-9 kamu sudah aku simpan."

    return FakeLLM(responder=respond)


# Metadata simulation (frontend contract)


def build_phq9_metadata(state: ConversationState) -> dict[str, Any] | None:
    phq9 = state.get("phq9_state") or {}
    phase = phq9.get("phase", "idle")
    language = phq9.get("language") or state.get("resolved_language") or "id"

    if phase in (None, "idle", "offer_pending"):
        return None

    payload: dict[str, Any] = {
        "active": phase in ("offered", "in_progress", "awaiting_clar"),
        "phase": phase,
        "language": language,
        "allow_free_text": True,
    }

    if phase == "offered":
        payload["options"] = [
            {"score": None, "label": "Accept" if language == "en" else "Mulai"},
            {"score": None, "label": "Decline" if language == "en" else "Lewati"},
        ]
        payload["progress"] = {"current": 0, "total": NUM_ITEMS}
        return payload

    if phase in ("in_progress", "awaiting_clar"):
        item_id = int(phq9.get("active_item") or 1)
        payload["item_id"] = item_id
        payload["options"] = [
            {"score": score, "label": label} for score, label in options_with_scores(language)
        ]
        payload["progress"] = {"current": item_id, "total": NUM_ITEMS}
        return payload

    # completed / declined / deferred_crisis: treat as plain chat
    payload["active"] = False
    payload["progress"] = {"current": NUM_ITEMS, "total": NUM_ITEMS}
    return payload



def _print_assistant(state: ConversationState) -> None:
    text = (state.get("response_draft") or "").strip()
    if text:
        print("\nassistant:")
        print(text)

    md = build_phq9_metadata(state)
    if md is not None:
        print("\nmetadata.phq9:")
        print(json.dumps(md, ensure_ascii=False, indent=2))

    phq9 = state.get("phq9_state") or {}
    if phq9.get("phase") in ("completed", "deferred_crisis"):
        print("\n(phq9) phase=", phq9.get("phase"), "route_to_crisis_after=", phq9.get("route_to_crisis_after"))


async def _step(state: ConversationState, *, repo: Any, scorer_llm: Any, feedback_llm: Any) -> ConversationState:
    # PHQ-9 trigger evaluation (idempotent).
    state = await phq9_check_node(state, repo=repo)

    # Route to delivery if assessment is engaged.
    phq9 = state.get("phq9_state") or {}
    if phq9.get("phase") in ("offer_pending", "offered", "in_progress", "awaiting_clar"):
        state = await phq9_delivery_node(state, repo=repo, scorer_llm=scorer_llm, feedback_llm=feedback_llm)

    # Persist assistant message to history so future language resolution has context.
    if state.get("response_draft"):
        state["messages"].append({"role": "assistant", "content": state["response_draft"]})

    return state


def _bootstrap_state(*, args: argparse.Namespace) -> ConversationState:
    lang_pref = None if args.language == "auto" else args.language
    state = empty_conversation_state(
        user_id=args.user_id,
        session_id=args.session_id,
        language_pref=lang_pref,
    )

    # Optional: force a starting PHQ-9 phase for quick testing.
    if args.bootstrap_phase and args.bootstrap_phase != "idle":
        phq9 = empty_phq9_state()
        phq9["phase"] = args.bootstrap_phase  # type: ignore[assignment]
        phq9["tier"] = "scheduled"  # type: ignore[assignment]
        phq9["language"] = (lang_pref or "id")
        if args.bootstrap_phase in ("in_progress", "awaiting_clar"):
            phq9["active_item"] = 1
        state["phq9_state"] = phq9
        state["resolved_language"] = phq9["language"]

    return state


async def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive assessment CLI bot (PHQ-9).")
    parser.add_argument("--user-id", default="test-user", help="User id")
    parser.add_argument("--session-id", default="test-session", help="Session id")
    parser.add_argument("--language", choices=["id", "en", "auto"], default="auto")
    parser.add_argument(
        "--bootstrap-phase",
        choices=["idle", "offer_pending", "offered", "in_progress", "awaiting_clar"],
        default="idle",
        help="Force initial PHQ-9 phase for debugging",
    )
    args = parser.parse_args()

    repo = InMemoryAssessmentRepository()
    state = _bootstrap_state(args=args)

    scorer_llm = build_fake_scorer_llm()
    # Feedback language should follow resolved language once set.
    feedback_llm = build_fake_feedback_llm(args.language if args.language != "auto" else "id")

    print("Assessment CLI bot (PHQ-9)")
    print("- Type messages and press Enter")
    print("- Type 'quit' to exit")
    print("- When options are shown, send '0'..'3' as a button tap")

    while True:
        try:
            user_text = input("\nuser: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return 0

        if user_text.lower() in {"quit", "exit", ":q"}:
            print("Exiting.")
            return 0

        # New turn.
        state["session_turn"] = int(state.get("session_turn", 0)) + 1
        state["current_message"] = user_text
        state["messages"].append({"role": "user", "content": user_text})

        # Clear previous response.
        state.pop("response_draft", None)

        state = await _step(state, repo=repo, scorer_llm=scorer_llm, feedback_llm=feedback_llm)
        _print_assistant(state)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

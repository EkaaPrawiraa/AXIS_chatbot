"""Compiled LangGraph subgraph that owns PHQ-9 administration."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)  # noqa: F401  (events used by future audit hooks)
from agentic.agent.phq9.judge import (
    JudgeAction,
    JudgeOutcome,
    judge_item_response,
)
from agentic.agent.state import ConversationState, empty_phq9_state
from agentic.assessment.conversational_delivery import (
    build_acknowledgement,
    build_clarification,
    build_clarification_explanation,
    build_feedback_message,
    build_greeting,
    build_item_prompt,
    build_offer,
)
from agentic.assessment.phq9 import (
    ITEM9_INDEX_ONE_BASED,
    NUM_ITEMS,
    PHQ9Response,
    ResponseSource,
    score_phq9,
)
from agentic.memory.assessment_repo import AssessmentRepository


logger = logging.getLogger(__name__)



MAX_BACK_NAVIGATIONS: int = 2
WARMUP_TURNS_BEFORE_OFFER: int = 5  # mirrors phq9_delivery legacy
DECLINED_OFFER_RETRY_DAYS: int = 3


_DECLINE_CUES_ID: tuple[str, ...] = (
    "engga", "tidak", "ga", "gak", "nanti", "skip", "lewatin",
    "ga mau", "lain kali", "nggak deh",
    "ngobrol dulu", "obrol dulu", "curhat dulu", "cerita dulu",
)
_DECLINE_CUES_EN: tuple[str, ...] = (
    "no thanks", "skip", "later", "not now", "rather chat",
)
_ACCEPT_CUES_ID: tuple[str, ...] = (
    "iya", "boleh", "oke", "ok", "yuk", "mulai", "ayo", "gas", "bisa", "sabi", "lanjut", "sok", "silahkan",
)
_ACCEPT_CUES_EN: tuple[str, ...] = (
    "yes", "ok", "okay", "sure", "let's", "lets do",
)



def _phq9(state: ConversationState) -> dict[str, Any]:
    return dict(state.get("phq9_state") or empty_phq9_state())


def _commit(state: ConversationState, phq9: dict[str, Any]) -> None:
    state["phq9_state"] = phq9  # type: ignore[typeddict-item]


def _is_decline(reply: str, language: str) -> bool:
    if not reply:
        return False
    lower = _MULTI_SPACE_RE.sub(" ", reply.lower()).strip()
    cues = _DECLINE_CUES_ID if language == "id" else _DECLINE_CUES_EN
    return any(_cue_matches(lower, cue) for cue in cues)


def _is_accept(reply: str, language: str) -> bool:
    if not reply:
        return False
    lower = _MULTI_SPACE_RE.sub(" ", reply.lower()).strip()
    cues = _ACCEPT_CUES_ID if language == "id" else _ACCEPT_CUES_EN
    return any(_cue_matches(lower, cue) for cue in cues)


_MULTI_SPACE_RE = re.compile(r"\s+")


def _cue_matches(text: str, cue: str) -> bool:
    escaped = re.escape(cue.strip())
    if not escaped:
        return False
    return re.search(rf"(^|\W){escaped}($|\W)", text) is not None


def _decline_message(language: str) -> str:
    if language == "id":
        return (
            "Oke, kita lewat dulu. Kalau kamu mau ngobrol biasa atau "
            "balik lagi ke topik tadi, aku ikut aja."
        )
    return (
        "No problem, we'll skip it for now. Happy to keep chatting "
        "or pick up wherever you'd like."
    )


def _continue_chat_message(language: str) -> str:
    if language == "id":
        return (
            "Oke, kita ngobrol dulu. Aku tetap di sini. "
            "Kamu mau mulai cerita dari bagian mana?"
        )
    return (
        "Okay, we can keep talking. I'm here with you. "
        "Where would you like to start?"
    )


def _recent_context(state: ConversationState) -> str:
    history = state.get("messages") or []
    tail = list(history)[-6:]
    parts: list[str] = []
    for msg in tail:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"{role.title() if role else 'Other'}: {content}")
    return "\n".join(parts)



async def _persist_progress(
    repo: AssessmentRepository,
    user_id: str,
    session_id: str,
    phq9: dict[str, Any],
) -> None:
    """UPSERT in-flight PHQ-9 progress; never raise.

    Persistence failure must never break the user-facing flow. If the
    DB is hiccupping we log and continue; the next save will reconcile.
    The caller side (request/response round-trip) still carries the
    canonical state for this turn.
    """
    if not user_id or not session_id:
        return
    try:
        await repo.save_phq9_progress(
            user_id=user_id, session_id=session_id, state=phq9,
        )
    except Exception as exc:  # pragma: no cover defensive
        logger.warning(
            "phq9 progress persist failed for %s/%s: %s",
            user_id, session_id, exc,
        )


async def _clear_progress(
    repo: AssessmentRepository,
    user_id: str,
    session_id: str,
) -> None:
    """Drop the in-flight row after the run terminates (declined/done)."""
    if not user_id or not session_id:
        return
    try:
        await repo.clear_phq9_progress(
            user_id=user_id, session_id=session_id,
        )
    except Exception as exc:  # pragma: no cover defensive
        logger.warning(
            "phq9 progress clear failed for %s/%s: %s",
            user_id, session_id, exc,
        )


async def _schedule_declined_retry(
    repo: AssessmentRepository,
    user_id: str,
) -> None:
    if not user_id:
        return
    try:
        await repo.schedule_retry(
            user_id=user_id,
            days=DECLINED_OFFER_RETRY_DAYS,
            reason="declined_offer",
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("phq9 declined-offer retry failed for %s: %s", user_id, exc)


# Explanation request detection
_EXPLANATION_CUES_ID: tuple[re.Pattern[str], ...] = (
    # 1. Formal / baku
    re.compile(r"\b(maksudnya|maksud pertanyaannya|gimana maksudnya)\b", re.IGNORECASE),
    re.compile(r"\b(apa (sih )?(yang )?dimaksud)\b", re.IGNORECASE),
    re.compile(r"\b(apa artinya|artinya apa)\b", re.IGNORECASE),
    re.compile(r"\b(jelaskan|definisi|jelasin)\b", re.IGNORECASE),
    re.compile(r"\b(bisa (di)?(per)?jelas(kan|in)?)\b", re.IGNORECASE),
    # 2. Colloquial / gaul
    re.compile(r"\b(gimana maksudnya|gimana sih|maksudnya gimana)\b", re.IGNORECASE),
    re.compile(r"\b(ga|gak|nggak|engga|enggak)\s+(ngerti|paham|jelas)\b", re.IGNORECASE),
    re.compile(r"\bbingung\b", re.IGNORECASE),
    re.compile(r"\b(contoh(nya)?( gimana)?|contoh dong)\b", re.IGNORECASE),
)
_EXPLANATION_CUES_EN: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(what do(es)? (this|that) mean)\b", re.IGNORECASE),
    re.compile(r"\b(what do you mean)\b", re.IGNORECASE),
    re.compile(r"\b(meaning of (this|that)( question)?)\b", re.IGNORECASE),
    re.compile(r"\b(explain|clarify)\b", re.IGNORECASE),
    re.compile(r"\b(i\s*(don'?t|do not)\s+understand)\b", re.IGNORECASE),
    re.compile(r"\b(give me an example|example\?)\b", re.IGNORECASE),
)


def _is_explanation_request(reply: str, language: str) -> bool:
    """Return True if the user is asking the bot to explain the item.

    Checks ID cues first, then EN, regardless of declared language so
    code-switched messages ("jelasin what does this mean") fire too.
    """
    if not reply:
        return False
    primary = _EXPLANATION_CUES_ID if language == "id" else _EXPLANATION_CUES_EN
    secondary = _EXPLANATION_CUES_EN if language == "id" else _EXPLANATION_CUES_ID
    return any(p.search(reply) for p in primary) or any(
        p.search(reply) for p in secondary
    )


# Node: offer


async def _node_offer(
    state: ConversationState,
    *,
    audit: GuardrailLogger,
) -> ConversationState:
    """
    Phase 2 implementation: this node no longer emits a static line.
    Instead, it ARMS the response generator with an offer directive
    and lets the LLM weave the invitation into a contextual reply.

    The phase stays ``offer_pending``. When the response generator
    finishes, it sets ``phq9_state.phase = "offered"`` and clears the
    armed flag, so the next user reply hits the decision node.

    Static text is only used as a last-resort fallback when warm-up
    has long elapsed and the response generator never weaved the
    offer (e.g., LLM downtime).
    """
    phq9 = _phq9(state)
    if int(state.get("session_turn") or 0) < WARMUP_TURNS_BEFORE_OFFER:
        phq9["offer_armed"] = False
        _commit(state, phq9)
        return state

    phq9["offer_armed"] = True
    _commit(state, phq9)
    return state


# Node: process accept/decline reply


async def _node_decision(
    state: ConversationState,
    *,
    audit: GuardrailLogger,
    repo: AssessmentRepository,
) -> ConversationState:
    phq9 = _phq9(state)
    language = phq9.get("language") or "id"
    reply = (state.get("current_message") or "").strip()
    user_id = state.get("user_id") or ""
    session_id = state.get("session_id") or ""

    if phq9.get("user_initiated"):
        out = _accept_and_start_item1(state, phq9, language)
        await _persist_progress(
            repo,
            state.get("user_id") or "",
            state.get("session_id") or "",
            out.get("phq9_state") or {},
        )
        return out

    if _is_decline(reply, language):
        phq9["phase"] = "declined"
        _commit(state, phq9)
        state["phq9_declined_note"] = True  # type: ignore[typeddict-unknown-key]
        await _clear_progress(repo, user_id, session_id)
        await _schedule_declined_retry(repo, user_id)
        return state

    if not _is_accept(reply, language):
        phq9["phase"] = "idle"
        phq9["offer_armed"] = False
        _commit(state, phq9)
        state["phq9_declined_note"] = True  # type: ignore[typeddict-unknown-key]
        await _clear_progress(repo, user_id, session_id)
        await _schedule_declined_retry(repo, user_id)
        return state

    out = _accept_and_start_item1(state, phq9, language)
    await _persist_progress(
        repo,
        state.get("user_id") or "",
        state.get("session_id") or "",
        out.get("phq9_state") or {},
    )
    return out


def _accept_and_start_item1(
    state: ConversationState,
    phq9: dict[str, Any],
    language: str,
) -> ConversationState:
    """Enter item 1 with greeting + first prompt."""
    phq9["phase"] = "in_progress"
    phq9["active_item"] = 1
    phq9["responses"] = {}
    phq9["awaiting_clarification"] = False
    phq9["back_count"] = 0
    phq9["offer_armed"] = False
    state["response_draft"] = (
        build_greeting(language) + "\n\n" + build_item_prompt(1, language)
    )
    _commit(state, phq9)
    return state


# Node: item delivery (items 1..9)


async def _node_item(
    state: ConversationState,
    *,
    audit: GuardrailLogger,
    judge_llm: Any | None,
    clarification_llm: Any | None,
    repo: AssessmentRepository,
    feedback_llm: Any | None,
) -> ConversationState:
    phq9 = _phq9(state)
    language = phq9.get("language") or "id"
    item_id = int(phq9.get("active_item") or 1)
    user_reply = (state.get("current_message") or "").strip()
    was_awaiting_clarification = phq9.get("phase") == "awaiting_clar"
    user_id = state.get("user_id") or ""
    session_id = state.get("session_id") or ""

    # Short-circuit: user is asking, not answerins
    if _is_explanation_request(user_reply, language):
        phq9["phase"] = "awaiting_clar"
        phq9["awaiting_clarification"] = True
        state["response_draft"] = await build_clarification_explanation(
            item_id=item_id,
            language=language,
            prior_text=user_reply,
            recent_context=_recent_context(state),
            llm=clarification_llm,
        )
        _commit(state, phq9)
        await _persist_progress(repo, user_id, session_id, phq9)
        return state

    # Run the judge on the user's reply.
    outcome = await judge_item_response(
        item_id=item_id,
        user_reply=user_reply,
        language=language,
        recent_context=_recent_context(state),
        llm=judge_llm,
    )

    # Item 9 safety override
    action = outcome.action
    if item_id == ITEM9_INDEX_ONE_BASED and action != JudgeAction.STOP:
        action = JudgeAction.ADVANCE

    phq9["last_judge_action"] = action.value
    phq9["last_judge_rationale"] = outcome.rationale

    if action == JudgeAction.DECLINE:
        phq9["phase"] = "declined"
        state["response_draft"] = _decline_message(language)
        _commit(state, phq9)
        # Decline ends the run; clear in-flight progress.
        await _clear_progress(repo, user_id, session_id)
        return state

    if action == JudgeAction.STOP:
        # Bail out without scoring. Crisis pre-gen will own the next turn.
        state["safety_flag"] = "crisis"  # signal main graph
        _commit(state, phq9)
        # Keep progress row so we can resume
        await _persist_progress(repo, user_id, session_id, phq9)
        return state

    if action == JudgeAction.CLARIFY and was_awaiting_clarification:
        action = JudgeAction.ADVANCE

    if action == JudgeAction.CLARIFY:
        phq9["phase"] = "awaiting_clar"
        phq9["awaiting_clarification"] = True
        state["response_draft"] = build_clarification(
            item_id, language, user_reply,
        )
        _commit(state, phq9)
        await _persist_progress(repo, user_id, session_id, phq9)
        return state

    if action == JudgeAction.BACK:
        target = outcome.next_item or max(item_id - 1, 1)
        if phq9.get("back_count", 0) >= MAX_BACK_NAVIGATIONS:
            phq9["phase"] = "awaiting_clar"
            phq9["awaiting_clarification"] = True
            state["response_draft"] = build_clarification(
                item_id, language, user_reply,
            )
            _commit(state, phq9)
            await _persist_progress(repo, user_id, session_id, phq9)
            return state
        phq9["back_count"] = int(phq9.get("back_count", 0)) + 1
        phq9["active_item"] = target
        phq9["awaiting_clarification"] = False
        # Re-present the target item.
        state["response_draft"] = build_item_prompt(target, language)
        _commit(state, phq9)
        await _persist_progress(repo, user_id, session_id, phq9)
        return state

    # ADVANCE path: persist the response, move pointer, surface next.
    responses = dict(phq9.get("responses") or {})
    response_source = (
        ResponseSource.BUTTON
        if re.fullmatch(r"\s*[0-3]\s*", user_reply or "")
        else ResponseSource.TEXT_LLM
    )
    responses[item_id] = {
        "score": int(outcome.score),
        "source": response_source.value,
        "raw_text": user_reply,
        "confidence": float(outcome.confidence),
    }
    phq9["responses"] = responses
    phq9["awaiting_clarification"] = False
    # Commit before any further branch so _node_finalize re-reads the
    # latest responses dict from state.
    _commit(state, phq9)

    if item_id < NUM_ITEMS:
        next_id = item_id + 1
        phq9["active_item"] = next_id
        phq9["phase"] = "in_progress"
        state["response_draft"] = (
            build_acknowledgement(item_id, language)
            + "\n\n"
            + build_item_prompt(next_id, language)
        )
        _commit(state, phq9)
        # Persist the in-flight progress after every accepted item so a
        # crash or stateless restart can resume without losing scores.
        await _persist_progress(repo, user_id, session_id, phq9)
        return state

    # Reached the end: finalize.
    return await _node_finalize(
        state, audit=audit, repo=repo, feedback_llm=feedback_llm,
    )


# Node: finalize


async def _node_finalize(
    state: ConversationState,
    *,
    audit: GuardrailLogger,
    repo: AssessmentRepository,
    feedback_llm: Any | None,
) -> ConversationState:
    phq9 = _phq9(state)
    language = phq9.get("language") or "id"
    user_id = state.get("user_id") or ""
    session_id = state.get("session_id") or ""
    responses_dict = phq9.get("responses") or {}

    response_objs = [
        PHQ9Response(
            item_id=int(item_id),
            score=int(payload["score"]),
            source=ResponseSource(payload["source"]),
            raw_text=payload.get("raw_text"),
            confidence=payload.get("confidence"),
        )
        for item_id, payload in sorted(
            responses_dict.items(), key=lambda kv: int(kv[0])
        )
    ]

    if len(response_objs) < NUM_ITEMS:
        # Partial completion (e.g. user declined mid-flight). Skip
        # scoring; phase is already declined or stays in_progress.
        _commit(state, phq9)
        return state

    last_snapshot = await repo.get_last_phq9(user_id) if user_id else None
    previous_total = (
        last_snapshot.total_score if last_snapshot is not None else None
    )

    result = score_phq9(
        user_id=user_id,
        session_id=session_id,
        responses=response_objs,
        language=language,
        previous_total=previous_total,
        administered_at=datetime.now(timezone.utc),
    )

    try:
        await repo.save_phq9_result(result)
        await repo.clear_retry(user_id)
        # Run is now in the assessments table; drop the in-flight row.
        await _clear_progress(repo, user_id, session_id)
    except Exception as exc:
        logger.exception("phq9 persist failed: %s", exc)

    feedback = await build_feedback_message(
        total_score=result.total_score,
        severity=result.severity,
        item_scores=result.item_scores,
        language=language,
        item9_flagged=result.item9_flagged,
        llm=feedback_llm,
    )

    phq9["phase"] = "deferred_crisis" if result.item9_flagged else "completed"
    phq9["last_total"] = result.total_score
    phq9["last_severity"] = result.severity.value
    phq9["item9_flagged"] = result.item9_flagged
    phq9["route_to_crisis_after"] = result.item9_flagged

    state["response_draft"] = feedback
    _commit(state, phq9)
    if result.item9_flagged:
        state["safety_flag"] = "escalate"
    return state



def _route_entry(state: ConversationState) -> str:
    phase = (state.get("phq9_state") or {}).get("phase", "idle")
    if phase == "offer_pending":
        return "offer"
    if phase == "offered":
        return "decision"
    if phase in ("in_progress", "awaiting_clar"):
        return "item"
    if phase == "completed" or phase == "deferred_crisis":
        return "passthrough"
    return "passthrough"


async def _node_passthrough(state: ConversationState) -> ConversationState:
    return state



def build_phq9_subgraph(
    *,
    repo: AssessmentRepository,
    judge_llm: Any | None = None,
    clarification_llm: Any | None = None,
    feedback_llm: Any | None = None,
    audit: GuardrailLogger | None = None,
) -> Any:
    """
    Compile the PHQ-9 subgraph as a LangGraph CompiledGraph. Returned
    object satisfies the same protocol as any other LangGraph node, so
    the main graph can wire it via ``add_node("phq9_delivery", subgraph)``.
    """
    from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]

    audit = audit or NullGuardrailLogger()

    async def offer_wrapped(state: ConversationState) -> ConversationState:
        return await _node_offer(state, audit=audit)

    async def decision_wrapped(state: ConversationState) -> ConversationState:
        return await _node_decision(state, audit=audit, repo=repo)

    async def item_wrapped(state: ConversationState) -> ConversationState:
        return await _node_item(
            state,
            audit=audit,
            judge_llm=judge_llm,
            clarification_llm=clarification_llm,
            repo=repo,
            feedback_llm=feedback_llm,
        )

    g: Any = StateGraph(ConversationState)
    g.add_node("offer", offer_wrapped)
    g.add_node("decision", decision_wrapped)
    g.add_node("item", item_wrapped)
    g.add_node("passthrough", _node_passthrough)
    g.set_conditional_entry_point(
        _route_entry,
        {
            "offer": "offer",
            "decision": "decision",
            "item": "item",
            "passthrough": "passthrough",
        },
    )
    g.add_edge("offer", END)
    g.add_edge("decision", END)
    g.add_edge("item", END)
    g.add_edge("passthrough", END)
    return g.compile()


# Plain-Python wrapper (used by the existing phq9_delivery_node)


async def phq9_subgraph_node(
    state: ConversationState,
    *,
    repo: AssessmentRepository,
    judge_llm: Any | None = None,
    clarification_llm: Any | None = None,
    feedback_llm: Any | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """
    Run one PHQ-9 subgraph step without requiring LangGraph. The main
    graph can use either this Python entry point (cheap and portable)
    or :func:`build_phq9_subgraph` (LangSmith tracing).
    """
    audit = audit or NullGuardrailLogger()
    phase = (state.get("phq9_state") or {}).get("phase", "idle")
    if phase == "offer_pending":
        return await _node_offer(state, audit=audit)
    if phase == "offered":
        return await _node_decision(state, audit=audit, repo=repo)
    if phase in ("in_progress", "awaiting_clar"):
        return await _node_item(
            state,
            audit=audit,
            judge_llm=judge_llm,
            clarification_llm=clarification_llm,
            repo=repo,
            feedback_llm=feedback_llm,
        )
    return state


__all__ = [
    "MAX_BACK_NAVIGATIONS",
    "WARMUP_TURNS_BEFORE_OFFER",
    "build_phq9_subgraph",
    "phq9_subgraph_node",
]

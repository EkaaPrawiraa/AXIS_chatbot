"""`trigger phq-9`"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.state import (
    ConversationState,
    PHQ9SessionState,
    empty_phq9_state,
)
from agentic.assessment.phq9 import resolve_language
from agentic.memory.assessment_repo import (
    ACUTE_DISTRESS_VALENCE_THRESHOLD,
    AssessmentRepository,
    LOOKBACK_DAYS_FOR_KG,
    WORSENING_DELTA_THRESHOLD,
    days_since,
)


logger = logging.getLogger(__name__)



SCHEDULED_INTERVAL_DAYS: int = 14
RETRY_DAYS_FOR_DISTRESS: int = 3
RETRY_DAYS_FOR_WORSENING: int = 7
EVENT_TIER_MIN_DISTRESS_SESSIONS: int = 2
# init state
WARMUP_CONVERSATIONS_BEFORE_FIRST_OFFER: int = 5


# init PHQ-9
import re as _re

USER_REQUEST_PATTERNS: tuple[_re.Pattern[str], ...] = (
    _re.compile(r"\bphq[\s-]?9\b", _re.IGNORECASE),
    _re.compile(r"\b(tes|cek|check[\s-]?in|kuesioner)\s+(mood|kondisi|mental)\b",
                _re.IGNORECASE),
    _re.compile(r"\b(mau|pengen|minta|bisa|let'?s)\s+(coba|jalanin|isi|do)\s+"
                r"(phq|tes|cek|check|kuesioner|questionnaire|assessment)",
                _re.IGNORECASE),
    _re.compile(r"\bmental\s+health\s+(check|questionnaire|test|assessment)\b",
                _re.IGNORECASE),
    _re.compile(r"\b(check|test)\s+my\s+(mood|mental\s+health)\b", _re.IGNORECASE),
    _re.compile(r"\b(ngecek|ngecek)\s+(mood|kondisi)\b", _re.IGNORECASE),
)


async def _persist_progress(
    repo: AssessmentRepository,
    *,
    user_id: str,
    session_id: str,
    phq9: PHQ9SessionState | dict[str, Any],
) -> None:
    if not user_id or not session_id:
        return
    try:
        await repo.save_phq9_progress(
            user_id=user_id,
            session_id=session_id,
            state=phq9,
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "phq9 trigger progress persist failed user=%s session=%s: %s",
            user_id,
            session_id,
            exc,
        )


def _is_user_request(message: str) -> bool:
    if not message:
        return False
    return any(p.search(message) for p in USER_REQUEST_PATTERNS)



async def phq9_check_node(
    state: ConversationState,
    *,
    repo: AssessmentRepository,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """evaluate, update, idempotent, idle, short-circuit, state"""
    audit = audit or NullGuardrailLogger()

    # skip PHQ-9
    if state.get("confession_mode"):
        state["phq9_state"] = empty_phq9_state()
        return state

    phq9 = state.get("phq9_state") or empty_phq9_state()
    user_id = state["user_id"]
    session_id = state.get("session_id") or ""

    # reload from db
    try:
        persisted = await repo.load_phq9_progress(
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as exc:  # pragma: no cover defensive
        logger.warning(
            "phq9 progress load failed; falling back to request state: %s",
            exc,
        )
        persisted = None

    if persisted is not None:
        persisted_phase = persisted.get("phase")
        request_phase = phq9.get("phase")
        if persisted_phase in (
            "offer_pending",
            "offered",
            "in_progress",
            "awaiting_clar",
        ):
            req_active = phq9.get("active_item")
            db_active = persisted.get("active_item")
            if (
                req_active is not None
                and db_active is not None
                and req_active != db_active
            ):
                logger.warning(
                    "phq9 state mismatch user=%s session=%s; "
                    "request.active_item=%s persisted=%s; using persisted",
                    user_id, session_id, req_active, db_active,
                )
            if request_phase not in ("offered", "in_progress", "awaiting_clar"):
                logger.info(
                    "phq9 progress rehydrated user=%s session=%s; "
                    "request.phase=%s persisted.phase=%s persisted.active_item=%s "
                    "scores=%d",
                    user_id,
                    session_id,
                    request_phase,
                    persisted_phase,
                    db_active,
                    len(persisted.get("responses") or {}),
                )
            merged = dict(phq9)
            merged.update(persisted)
            phq9 = merged  # type: ignore[assignment]
            state["phq9_state"] = phq9
            if persisted_phase != "offer_pending":
                return state

    # arm response gen dir" "warm-up turns" "phase engaged" "trigger node" "subgraph
    if phq9.get("phase") == "offer_pending":
        from agentic.agent.phq9.subgraph import WARMUP_TURNS_BEFORE_OFFER

        turn = int(state.get("session_turn") or 0)
        phq9 = dict(phq9)
        phq9["offer_armed"] = turn >= WARMUP_TURNS_BEFORE_OFFER
        state["phq9_state"] = phq9
        return state

    # skip assessment
    if phq9.get("phase") not in (None, "idle"):
        state["phq9_state"] = phq9
        return state

    # resolve lang
    language = state.get("resolved_language") or _resolve_language_for_state(state)
    state["resolved_language"] = language
    phq9["language"] = language

    # skip 14-day gate skip warm-up move to offered default accept
    user_msg = (state.get("current_message") or "").strip()
    if _is_user_request(user_msg):
        logger.info(
            "phq9 user-initiated request detected for %s: %r",
            user_id, user_msg[:80],
        )
        phq9["phase"] = "offered"
        phq9["tier"] = "scheduled"
        phq9["reason"] = "user_initiated"
        phq9["user_initiated"] = True
        phq9["offer_armed"] = False
        state["phq9_state"] = phq9
        await _persist_progress(
            repo,
            user_id=user_id,
            session_id=session_id,
            phq9=phq9,
        )
        await audit.log(GuardrailEvent(
            user_id=user_id,
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.KG_ACCESS,
            event_type="phq9_trigger_user_initiated",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=user_msg[:100],
        ))
        return state

    pending = await repo.get_pending_retry(user_id)
    if pending and pending.next_attempt_at > datetime.now(timezone.utc):
        phq9["retry_scheduled_at"] = pending.next_attempt_at.isoformat()
        phq9["reason"] = f"suppressed:{pending.reason}"
        state["phq9_state"] = phq9
        return state

    # `run tier 1`
    tier1 = await _evaluate_tier1(state, repo, phq9)
    if tier1 is not None:
        phq9 = tier1

    # menghitung tier 2 hanya jika tier 1 gagal.
    if phq9.get("phase") == "idle":
        tier2 = await _evaluate_tier2(state, repo, phq9)
        if tier2 is not None:
            phq9 = tier2

    state["phq9_state"] = phq9
    if phq9.get("phase") == "offer_pending":
        await _persist_progress(
            repo,
            user_id=user_id,
            session_id=session_id,
            phq9=phq9,
        )

    # audit: log non-trivial decisions.
    phase = phq9.get("phase") or "idle"
    reason = phq9.get("reason") or ""
    if phase == "offer_pending":
        await audit.log(GuardrailEvent(
            user_id=user_id,
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.KG_ACCESS,
            event_type="phq9_trigger_offer_pending",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=f"tier={phq9.get('tier')} reason={reason}",
        ))
    elif reason.startswith("suppressed:"):
        await audit.log(GuardrailEvent(
            user_id=user_id,
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.KG_ACCESS,
            event_type="phq9_trigger_suppressed",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.WARN,
            trigger_detail=f"reason={reason} retry={phq9.get('retry_scheduled_at')}",
        ))

    return state


# check every 14 days


async def _evaluate_tier1(
    state: ConversationState,
    repo: AssessmentRepository,
    phq9: PHQ9SessionState,
) -> PHQ9SessionState | None:
    """ret sub-state if tier 1 cond. satisfied"""
    user_id = state["user_id"]

    pending = await repo.get_pending_retry(user_id)
    if pending and pending.next_attempt_at > datetime.now(timezone.utc):
        phq9["retry_scheduled_at"] = pending.next_attempt_at.isoformat()
        return None

    last = await repo.get_last_phq9(user_id)
    if last is not None and days_since(last.administered_at) < SCHEDULED_INTERVAL_DAYS:
        return None

    # rapport, PHQ-9
    if last is None:
        convo_count = await repo.get_conversation_count(user_id)
        if convo_count < WARMUP_CONVERSATIONS_BEFORE_FIRST_OFFER:
            logger.info(
                "phq9 tier1 suppressed for %s: only %d completed conversation(s) "
                "(need %d before first offer)",
                user_id,
                convo_count,
                WARMUP_CONVERSATIONS_BEFORE_FIRST_OFFER,
            )
            return None

    if _acute_distress(state, await repo.get_distress_snapshot(user_id)):
        sched = await repo.schedule_retry(
            user_id=user_id,
            days=RETRY_DAYS_FOR_DISTRESS,
            reason="acute_distress",
        )
        phq9["retry_scheduled_at"] = sched.next_attempt_at.isoformat()
        phq9["reason"] = "suppressed:acute_distress"
        logger.info(
            "phq9 tier1 suppressed for %s due to acute distress, retry=%s",
            user_id,
            sched.next_attempt_at.isoformat(),
        )
        return phq9

    if _recently_worsened(last):
        sched = await repo.schedule_retry(
            user_id=user_id,
            days=RETRY_DAYS_FOR_WORSENING,
            reason="recent_worsening",
        )
        phq9["retry_scheduled_at"] = sched.next_attempt_at.isoformat()
        phq9["reason"] = "suppressed:recent_worsening"
        logger.info(
            "phq9 tier1 suppressed for %s due to recent worsening, retry=%s",
            user_id,
            sched.next_attempt_at.isoformat(),
        )
        return phq9

    # pending; wait for delivery.
    phq9["phase"] = "offer_pending"
    phq9["tier"] = "scheduled"
    phq9["reason"] = "scheduled_14d"
    phq9["offer_made_at_turn"] = None
    logger.info("phq9 tier1 offer pending for %s", user_id)
    return phq9


# event-based


async def _evaluate_tier2(
    state: ConversationState,
    repo: AssessmentRepository,
    phq9: PHQ9SessionState,
) -> PHQ9SessionState | None:
    """find distress signals, flag end-session."""
    user_id = state["user_id"]
    last = await repo.get_last_phq9(user_id)
    if last is not None and days_since(last.administered_at) < RETRY_DAYS_FOR_DISTRESS:
        phq9["reason"] = "suppressed:recent_phq9"
        return phq9

    snapshot = await repo.get_distress_snapshot(user_id)

    cluster_triggered = (
        snapshot.high_distress_session_count_7d >= EVENT_TIER_MIN_DISTRESS_SESSIONS
        or snapshot.recurring_trigger_active
    )
    if not cluster_triggered:
        return None

    # skip mid-convo, defer to next.
    if _acute_distress(state, snapshot):
        sched = await repo.schedule_retry(
            user_id=user_id,
            days=RETRY_DAYS_FOR_DISTRESS,
            reason="event_acute_distress",
        )
        phq9["retry_scheduled_at"] = sched.next_attempt_at.isoformat()
        phq9["reason"] = "suppressed:event_acute_distress"
        return phq9

    phq9["phase"] = "offer_pending"
    phq9["tier"] = "event"
    phq9["reason"] = _describe_event_cluster(snapshot)
    logger.info(
        "phq9 tier2 offer pending for %s (%s)",
        user_id,
        phq9["reason"],
    )
    return phq9



def _acute_distress(
    state: ConversationState,
    snapshot: Any,
) -> bool:
    del state  # signature kept for backward compat with call sites
    if snapshot is None:
        return False
    avg_v = snapshot.avg_emotion_valence_7d
    if avg_v is not None and avg_v <= ACUTE_DISTRESS_VALENCE_THRESHOLD:
        return True
    return False


def _recently_worsened(last: Any) -> bool:
    """``WORSENING_DELTA_THRESHOLD``"""
    if last is None:
        return False
    delta = getattr(last, "delta_from_prev", None)
    if delta is not None:
        # positive delta means score went up (worsened).
        return delta >= WORSENING_DELTA_THRESHOLD
    # fallback, severity 14, run 14-day gate
    return False


def _describe_event_cluster(snapshot: Any) -> str:
    parts = []
    if snapshot.high_distress_session_count_7d >= EVENT_TIER_MIN_DISTRESS_SESSIONS:
        parts.append(
            f"high_distress_sessions={snapshot.high_distress_session_count_7d}"
        )
    if snapshot.recurring_trigger_active:
        parts.append("recurring_trigger")
    return "event:" + ",".join(parts) if parts else "event:unknown"


def _resolve_language_for_state(state: ConversationState) -> str:
    """lang seluruh evaluasi."""
    msgs = [
        m.get("content", "")
        for m in (state.get("messages") or [])
        if m.get("role") == "user"
    ]
    if state.get("current_message"):
        msgs.append(state["current_message"])
    return resolve_language(
        user_pref=state.get("language_pref"),
        recent_messages=msgs[-5:],
    )




__all__ = [
    "phq9_check_node",
    "SCHEDULED_INTERVAL_DAYS",
    "RETRY_DAYS_FOR_DISTRESS",
    "RETRY_DAYS_FOR_WORSENING",
    "EVENT_TIER_MIN_DISTRESS_SESSIONS",
    "WARMUP_CONVERSATIONS_BEFORE_FIRST_OFFER",
]

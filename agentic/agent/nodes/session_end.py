"""Last node in the per-turn graph."""

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
from agentic.agent.session.activity_repo import SessionActivityRepository
from agentic.agent.state import ConversationState


logger = logging.getLogger(__name__)


def _build_phq9_metadata(state: ConversationState) -> dict[str, Any] | None:
    """
    Build the metadata.phq9 payload for the assistant message when a PHQ-9
    session is active. Returns None for idle / offer_pending phases so that
    plain messages are unaffected.
    """
    phq9 = state.get("phq9_state") or {}
    phase = phq9.get("phase", "idle")
    language: str = phq9.get("language") or state.get("resolved_language") or "id"

    if phase in (None, "idle", "offer_pending"):
        return None

    try:
        from agentic.assessment.phq9 import NUM_ITEMS, options_with_scores
    except Exception:
        return None

    active = phase in ("offered", "in_progress", "awaiting_clar")
    payload: dict[str, Any] = {
        "active": active,
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
            {"score": score, "label": label}
            for score, label in options_with_scores(language)
        ]
        payload["progress"] = {"current": item_id, "total": NUM_ITEMS}
        return payload

    # completed / declined / deferred_crisis → plain chat bubble, no chips
    payload["active"] = False
    payload["progress"] = {"current": NUM_ITEMS, "total": NUM_ITEMS}
    return payload


def _clean_response_text(text: str) -> str:
    return text.replace("—", "-").replace("–", "-")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_messages(state: ConversationState) -> bool:
    """
    Append the user message and the assistant reply into history.
    Returns True if an assistant reply was appended.
    """
    history: list[dict[str, Any]] = list(state.get("messages") or [])
    appended_user = False
    user_msg = (state.get("current_message") or "").strip()
    if user_msg:
        history.append({
            "role": "user",
            "content": user_msg,
            "ts": _now().isoformat(),
        })
        appended_user = True

    assistant_text = _clean_response_text(state.get("final_response") or "").strip()
    appended_assistant = False
    if assistant_text:
        state["final_response"] = assistant_text
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_text,
            "ts": _now().isoformat(),
        }
        phq9_meta = _build_phq9_metadata(state)
        if phq9_meta is not None:
            msg["metadata"] = {"phq9": phq9_meta}
        history.append(msg)
        appended_assistant = True

    if appended_user or appended_assistant:
        state["messages"] = history
    return appended_assistant


async def _persist_thought_record(state: ConversationState) -> None:
    """
    Write a completed CBT thought record to Neo4j.

    Silently no-ops when:
    - ``cbt_state`` is absent or has no ``thought_record``
    - ``thought_record["step"]`` is not ``"done"``
    - ``user_id`` or ``session_id`` is missing
    - Neo4j write fails (logged as warning, not re-raised)
    """
    cbt_state = state.get("cbt_state") or {}
    thought_record = cbt_state.get("thought_record")
    if not thought_record:
        return

    if thought_record.get("step") != "done":
        return

    user_id = state.get("user_id", "")
    session_id = state.get("session_id", "")
    if not user_id or not session_id:
        return

    try:
        from agentic.memory.knowledge_graph.kg_writer.thought_record_writer import (
            write_thought_record,
        )
        await write_thought_record(
            user_id=user_id,
            session_id=session_id,
            thought_record=thought_record,
        )
    except Exception as exc:
        logger.warning(
            "ThoughtRecord persist failed (user=%s session=%s): %s",
            user_id, session_id, exc,
        )


async def session_end_node(
    state: ConversationState,
    *,
    activity_repo: SessionActivityRepository | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """
    Update the message history, persist a completed thought record (if
    any), and record the session activity heartbeat.

    Safe to no-op when no ``activity_repo`` is wired (test bot or
    bootstrap scenarios). The thought record write is independently
    guarded and never raises.
    """
    audit = audit or NullGuardrailLogger()

    ai_replied = _append_messages(state)
    state["session_turn"] = int(state.get("session_turn") or 0) + 1

    # Persist completed CBT thought record to Neo4j (non-blocking on
    # failure — a failed write must not abort the chat response).
    await _persist_thought_record(state)

    # Confession Space keeps short-term/in-session context (messages were
    # already appended above) but must never enter the long-term KG/pgvector
    # pipeline — the activity heartbeat below is exactly what makes a
    # session eligible for SessionSweeper.finalize(), so skipping it here
    # is what makes the "no long-term memory" guarantee real.
    if (
        not state.get("confession_mode")
        and activity_repo is not None
        and state.get("user_id")
        and state.get("session_id")
    ):
        try:
            session_turn = int(state.get("session_turn") or 0)
            await activity_repo.upsert_activity(
                session_id=state["session_id"],
                user_id=state["user_id"],
                ai_was_last_speaker=ai_replied,
                latest_turn_index=max(0, (session_turn * 2) - 1),
            )
        except Exception as exc:
            logger.warning("session activity upsert failed: %s", exc)
            await audit.log(
                GuardrailEvent(
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    layer=GuardrailEventLayer.KG_ACCESS,
                    event_type="session_activity_upsert_error",
                    decision=GuardrailEventDecision.LOG_ONLY,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=str(exc)[:200],
                )
            )
            return state

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.KG_ACCESS,
            event_type="session_turn_end",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=("ai_last" if ai_replied else "user_last"),
        )
    )
    return state


__all__ = ["session_end_node"]

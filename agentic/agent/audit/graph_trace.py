"""Per-turn LangGraph trace capture and persistence."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Mapping

from agentic.agent.state import ConversationState


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_text(value: Any, *, limit: int = 220) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _safe_json(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, Mapping):
            return {str(k): _safe_json(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_safe_json(v) for v in value]
        return str(value)


def _phq9_summary(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not value:
        return None
    return {
        "phase": value.get("phase"),
        "tier": value.get("tier"),
        "reason": value.get("reason"),
        "active_item": value.get("active_item"),
        "last_judge_action": value.get("last_judge_action"),
        "last_judge_rationale": _short_text(value.get("last_judge_rationale")),
        "item9_flagged": value.get("item9_flagged"),
        "route_to_crisis_after": value.get("route_to_crisis_after"),
        "user_initiated": value.get("user_initiated"),
        "offer_armed": value.get("offer_armed"),
    }


def _retrieval_summary(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not value:
        return None
    summary: dict[str, Any] = {}
    for key in (
        "focused_recall",
        "safety_context",
        "identity_context",
        "recent_context",
        "semantic_context",
    ):
        bucket = value.get(key)
        if isinstance(bucket, list):
            summary[key] = len(bucket)
        elif bucket is not None:
            summary[key] = bucket
    for key in ("strategy", "query_original", "query_rewritten"):
        if value.get(key) is not None:
            summary[key] = _short_text(value.get(key))
    return summary or None


def graph_snapshot(state: ConversationState) -> dict[str, Any]:
    """Return a compact state summary suitable for audit logs."""
    input_guardrail = state.get("input_guardrail") or None
    cbt_state = state.get("cbt_state") or {}
    voice = state.get("voice_state") or {}
    return _safe_json({
        "session_turn": state.get("session_turn"),
        "resolved_language": state.get("resolved_language"),
        "safety_flag": state.get("safety_flag"),
        "crisis_tier": state.get("crisis_tier"),
        "deferred_crisis_signal": state.get("deferred_crisis_signal"),
        "input_guardrail": {
            "decision": input_guardrail.get("decision"),
            "reason": input_guardrail.get("reason"),
            "matched": input_guardrail.get("matched"),
        } if isinstance(input_guardrail, Mapping) else None,
        "linguistic_signals": state.get("linguistic_signals"),
        "phq9": _phq9_summary(state.get("phq9_state") or None),
        "cbt": {
            "active": state.get("cbt_node_active"),
            "directive": state.get("cbt_directive"),
            "last_offered": cbt_state.get("last_offered"),
            "declined_last_offer": cbt_state.get("declined_last_offer"),
            "decline_streak": cbt_state.get("decline_streak"),
            "thought_record_active": cbt_state.get("thought_record_active"),
            "thought_record": cbt_state.get("thought_record"),
        },
        "retrieval": {
            "kg_context_chars": len(state.get("kg_context") or ""),
            "has_kg_context": bool(state.get("kg_context")),
            "retrieval_context": _retrieval_summary(
                state.get("retrieval_context") or None
            ),
        },
        "voice": {
            "output_modality": voice.get("output_modality"),
            "has_audio_input": voice.get("audio_input") is not None,
            "has_transcript": bool(voice.get("transcript")),
            "tts_provider": voice.get("tts_provider"),
            "tts_model": voice.get("tts_model"),
            "voice_error": voice.get("voice_error"),
        },
        "response": {
            "has_response_draft": bool(state.get("response_draft")),
            "has_final_response": bool(state.get("final_response")),
            "response_draft_chars": len(state.get("response_draft") or ""),
            "final_response_chars": len(state.get("final_response") or ""),
        },
    })


def ensure_trace(state: ConversationState) -> dict[str, Any]:
    trace = state.get("graph_trace")
    if not isinstance(trace, dict):
        trace = {
            "nodes": [],
            "routes": [],
            "started_at": _now_iso(),
        }
        state["graph_trace"] = trace
    return trace


def trace_node_start(state: ConversationState, node: str) -> None:
    trace = ensure_trace(state)
    trace.setdefault("nodes", []).append({
        "node": node,
        "event": "start",
        "at": _now_iso(),
        "state": graph_snapshot(state),
    })


def trace_node_end(state: ConversationState, node: str) -> None:
    trace = ensure_trace(state)
    trace.setdefault("nodes", []).append({
        "node": node,
        "event": "end",
        "at": _now_iso(),
        "state": graph_snapshot(state),
    })


def trace_node_error(state: ConversationState, node: str, exc: BaseException) -> None:
    trace = ensure_trace(state)
    trace.setdefault("nodes", []).append({
        "node": node,
        "event": "error",
        "at": _now_iso(),
        "error": str(exc),
        "state": graph_snapshot(state),
    })


def trace_route(
    state: ConversationState,
    *,
    source: str,
    target: str,
    reason: str | None = None,
    condition: Mapping[str, Any] | None = None,
) -> str:
    trace = ensure_trace(state)
    trace.setdefault("routes", []).append({
        "source": source,
        "target": target,
        "reason": reason,
        "condition": _safe_json(dict(condition or {})),
        "at": _now_iso(),
    })
    return target


def finalize_trace(state: ConversationState) -> dict[str, Any]:
    trace = ensure_trace(state)
    trace["finished_at"] = _now_iso()
    trace["final_state"] = graph_snapshot(state)
    return _safe_json(trace)


async def persist_graph_audit(state: ConversationState) -> None:
    """Persist graph trace for normal, stored chat messages only."""
    if state.get("confession_mode"):
        return
    message_id = state.get("current_message_id")
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    if not message_id or not user_id:
        return
    message_content = (state.get("current_message") or "").strip()
    if not message_content:
        voice = state.get("voice_state") or {}
        message_content = (voice.get("transcript") or "").strip()
    if not message_content:
        return
    graph = finalize_trace(state)
    try:
        from agentic.memory.pg_vector.client import get_pool  # noqa: PLC0415

        pool = await get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agentic_graph_audits (
                    message_id, user_id, session_id, message_content, graph
                ) VALUES (
                    $1::uuid, $2::uuid, $3::uuid, $4, $5::jsonb
                )
                """,
                message_id,
                user_id,
                session_id,
                message_content,
                json.dumps(graph),
            )
    except Exception as exc:  # pragma: no cover - audit must never break chat
        logger.warning("agentic graph audit insert failed: %s", exc)

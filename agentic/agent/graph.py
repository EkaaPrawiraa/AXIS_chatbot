"""wiring."""

from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable

from agentic.agent.audit.guardrail_events import (
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.audit.graph_trace import (
    trace_node_end,
    trace_node_error,
    trace_node_start,
    trace_route,
)
from agentic.agent.nodes.crisis_guardrail import (
    crisis_empathy_node,
    crisis_escalation_node,
    crisis_guardrail_node,
    crisis_triage_node,
    route_after_crisis_triage,
)
from agentic.agent.nodes.dialogue_policy import dialogue_policy_node
from agentic.agent.nodes.input_guardrail import input_guardrail_node
from agentic.agent.nodes.linguistic_enrichment import linguistic_enrichment_node
from agentic.agent.nodes.memory_retrieval import (
    ContextBuilderFn,
    memory_retrieval_node,
)
from agentic.agent.nodes.output_guardrail import output_guardrail_node
from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.nodes.phq9_delivery import phq9_delivery_node
from agentic.agent.nodes.response_generator import response_generator_node
from agentic.agent.nodes.understanding_synthesis import understanding_synthesis_node
from agentic.agent.nodes.session_end import session_end_node
from agentic.agent.nodes.speech_adapter import speech_adapter_node
from agentic.agent.nodes.speech_to_text import (
    STTProvider,
    speech_to_text_node,
)
from agentic.agent.nodes.text_to_speech import (
    ElevenLabsTTSProvider,
    OpenAITTSProvider,
    text_to_speech_node,
)
from agentic.agent.session.activity_repo import SessionActivityRepository
from agentic.agent.state import ConversationState
from agentic.config.voices import VoiceCatalog
from agentic.memory.assessment_repo import AssessmentRepository


logger = logging.getLogger(__name__)


NodeFn = Callable[[ConversationState], Awaitable[ConversationState]]


async def _load_profile_context(user_id: str) -> dict[str, Any] | None:
    """load"""
    try:
        from agentic.memory.pg_vector.client import get_pool  # noqa: PLC0415

        pool = await get_pool()
        if not pool:
            return None
        row = await pool.fetchrow(
            """
            SELECT display_name, preferred_language, gender, onboarding_complete
            FROM users
            WHERE id = $1::uuid
            """,
            user_id,
        )
        if not row:
            return None
        context: dict[str, Any] = {
            "display_name": row["display_name"],
            "preferred_language": row["preferred_language"],
            "gender": row["gender"],
            "onboarding_complete": row["onboarding_complete"],
        }
        mood_context = await _load_mood_context(pool, user_id)
        if mood_context:
            context.update(mood_context)
        return context
    except Exception as exc:  # pragma: no cover
        logger.warning("_load_profile_context failed: %s", exc)
        return None


async def _load_mood_context(pool: Any, user_id: str) -> dict[str, str | None] | None:
    """load, mood, trend"""
    try:
        rows = await pool.fetch(
            """
            SELECT mood_date, mood_score
            FROM user_moods
            WHERE user_id = $1::uuid
              AND mood_date >= (NOW() AT TIME ZONE 'Asia/Jakarta')::date - INTERVAL '6 days'
            ORDER BY mood_date DESC
            """,
            user_id,
        )
        if not rows:
            return None
        today = str(rows[0]["mood_date"]) if rows[0]["mood_date"] else None
        is_today = today == _today_jakarta_date()
        return {
            "mood_today_score": str(rows[0]["mood_score"]) if is_today else None,
            "mood_trend": ",".join(str(r["mood_score"]) for r in reversed(rows)),
        }
    except Exception as exc:  # pragma: no cover
        logger.warning("_load_mood_context failed: %s", exc)
        return None


def _today_jakarta_date() -> str:
    from datetime import datetime, timezone, timedelta  # noqa: PLC0415

    return (datetime.now(timezone.utc) + timedelta(hours=7)).strftime("%Y-%m-%d")


async def _turn_init_node(state: ConversationState) -> ConversationState:
    """clean transients"""
    state["response_draft"] = None
    state["final_response"] = None

    state["safety_flag"] = None
    state["crisis_tier"] = None
    state["deferred_crisis_signal"] = False
    state.pop("input_guardrail", None)
    state.pop("crisis_escalated", None)

    state["kg_context"] = None

    user_id: str | None = state.get("user_id")
    if user_id:
        profile_context = await _load_profile_context(user_id)
        if profile_context:
            state["profile_context"] = profile_context

    # sync into db
    if (state.get("session_turn") or 0) == 0:
        if user_id:
            try:
                from agentic.memory.knowledge_graph.kg_writer import ensure_user_node  # noqa: PLC0415
                from agentic.memory.pg_vector.client import get_pool               # noqa: PLC0415

                pool = await get_pool()
                if pool:
                    await ensure_user_node(user_id=user_id, pg_pool=pool)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "_turn_init_node: ensure_user_node raised unexpectedly: %s", exc
                )

    return state


def route_entry(state: ConversationState) -> str:
    """skip klo text"""
    voice = state.get("voice_state") or {}
    if voice.get("audio_input") is not None:
        return trace_route(
            state,
            source="entry",
            target="speech_to_text",
            reason="audio_input_present",
            condition={"has_audio_input": True},
        )
    return trace_route(
        state,
        source="entry",
        target="input_guardrail_node",
        reason="text_turn",
        condition={"has_audio_input": False},
    )


def route_after_input_guardrail(state: ConversationState) -> str:
    """guardrail"""
    verdict = state.get("input_guardrail") or {}
    decision = verdict.get("decision")
    reason = verdict.get("reason", "")
    if decision == "escalate_crisis":
        return trace_route(
            state,
            source="input_guardrail_node",
            target="crisis_triage",
            reason="input_guardrail_escalate_crisis",
            condition={"decision": decision, "reason": reason},
        )
    if decision == "block":
        if reason == "off_scope":
            # skip llm, pass to voice, send
            return trace_route(
                state,
                source="input_guardrail_node",
                target="output_guardrail",
                reason="input_guardrail_off_scope_block",
                condition={"decision": decision, "reason": reason},
            )
        return trace_route(
            state,
            source="input_guardrail_node",
            target="response_generator",
            reason="input_guardrail_block_refusal_generation",
            condition={"decision": decision, "reason": reason},
        )
    return trace_route(
        state,
        source="input_guardrail_node",
        target="linguistic_enrichment",
        reason="input_guardrail_allow",
        condition={"decision": decision, "reason": reason},
    )


def route_after_output_finalized(state: ConversationState) -> str:
    """req payload"""
    voice = state.get("voice_state") or {}
    if voice.get("output_modality") in ("voice", "both"):
        return trace_route(
            state,
            source="post_guardrail_router",
            target="speech_adapter",
            reason="voice_output_requested",
            condition={"output_modality": voice.get("output_modality")},
        )
    return trace_route(
        state,
        source="post_guardrail_router",
        target="session_end",
        reason="text_output_only",
        condition={"output_modality": voice.get("output_modality")},
    )


def route_after_crisis_check(state: ConversationState) -> str:
    """gen pre"""
    if state.get("safety_flag") == "crisis":
        return trace_route(
            state,
            source="crisis_guardrail",
            target="crisis_triage",
            reason="crisis_guardrail_detected_crisis",
            condition={"safety_flag": state.get("safety_flag")},
        )
    return trace_route(
        state,
        source="crisis_guardrail",
        target="memory_retrieval",
        reason="crisis_guardrail_allow",
        condition={"safety_flag": state.get("safety_flag")},
    )


def route_after_dialogue(state: ConversationState) -> str:
    """route"""
    phq9 = state.get("phq9_state") or {}
    phase = phq9.get("phase", "idle")
    if phase == "offer_pending":
        return trace_route(
            state,
            source="dialogue_policy",
            target="response_generator",
            reason="phq9_offer_pending_generation",
            condition={"phase": phase, "offer_armed": phq9.get("offer_armed")},
        )
    if phase in ("offered", "in_progress", "awaiting_clar"):
        return trace_route(
            state,
            source="dialogue_policy",
            target="phq9_delivery",
            reason="phq9_active_or_offer_pending",
            condition={"phase": phase, "active_item": phq9.get("active_item")},
        )
    return trace_route(
        state,
        source="dialogue_policy",
        target="response_generator",
        reason="normal_response_generation",
        condition={"phase": phase, "cbt_node_active": state.get("cbt_node_active")},
    )


def route_after_phq9_delivery(state: ConversationState) -> str:
    """skip offer dismiss"""
    if state.get("phq9_declined_note") and not state.get("response_draft"):
        return trace_route(
            state,
            source="phq9_delivery",
            target="response_generator",
            reason="phq9_declined_needs_soft_response",
            condition={"phq9_declined_note": True},
        )
    return trace_route(
        state,
        source="phq9_delivery",
        target="output_guardrail",
        reason="phq9_delivery_completed_this_step",
        condition={
            "phq9_declined_note": bool(state.get("phq9_declined_note")),
            "has_response_draft": bool(state.get("response_draft")),
        },
    )


def route_after_output_guardrail(state: ConversationState) -> str:
    """safety."""
    phq9 = state.get("phq9_state") or {}
    if state.get("safety_flag") in ("crisis", "escalate"):
        return trace_route(
            state,
            source="output_guardrail",
            target="crisis_triage",
            reason="output_guardrail_or_state_safety_escalation",
            condition={"safety_flag": state.get("safety_flag")},
        )
    if phq9.get("route_to_crisis_after"):
        return trace_route(
            state,
            source="output_guardrail",
            target="crisis_escalation",
            reason="phq9_item9_deferred_crisis_route",
            condition={"route_to_crisis_after": True},
        )
    return trace_route(
        state,
        source="output_guardrail",
        target="session_end",
        reason="output_guardrail_allow",
        condition={"safety_flag": state.get("safety_flag")},
    )


def build_graph(
    *,
    assessment_repo: AssessmentRepository,
    scorer_llm: Any | None = None,
    feedback_llm: Any | None = None,
    rewrite_llm: Any | None = None,
    audit_logger: GuardrailLogger | None = None,
    stt_provider: STTProvider | None = None,
    elevenlabs_tts: ElevenLabsTTSProvider | None = None,
    openai_tts: OpenAITTSProvider | None = None,
    voice_catalog: VoiceCatalog | None = None,
    speech_adapter_llm_v25: Any | None = None,
    speech_adapter_llm_v3: Any | None = None,
    response_llm: Any | None = None,
    response_tools: list | None = None,
    phq9_judge_llm: Any | None = None,
    phq9_clarification_llm: Any | None = None,
    cbt_judge_llm: Any | None = None,
    crisis_empathy_llm: Any | None = None,
    context_builder: ContextBuilderFn | None = None,
    activity_repo: SessionActivityRepository | None = None,
    linguistic_node: NodeFn | None = None,
    memory_retrieval_node_fn: NodeFn | None = None,
    dialogue_policy_node_fn: NodeFn | None = None,
    response_generator_node_fn: NodeFn | None = None,
    session_end_node_fn: NodeFn | None = None,
    understanding_synthesis_llm: Any | None = None,
    understanding_synthesis_node_fn: NodeFn | None = None,
) -> Any:
    """build&compile"""
    from langgraph.graph import END, StateGraph

    audit = audit_logger or NullGuardrailLogger()

    def audited_node(name: str, fn: NodeFn) -> NodeFn:
        async def wrapped(state: ConversationState) -> ConversationState:
            trace_node_start(state, name)
            try:
                out = await fn(state)
            except Exception as exc:
                trace_node_error(state, name, exc)
                raise
            trace_node_end(out, name)
            return out

        return wrapped

    async def stt_wrapped(state: ConversationState) -> ConversationState:
        return await speech_to_text_node(
            state, provider=stt_provider, audit=audit,
        )

    async def speech_adapter_wrapped(state: ConversationState) -> ConversationState:
        return await speech_adapter_node(
            state,
            audit=audit,
            llm_v25=speech_adapter_llm_v25,
            llm_v3=speech_adapter_llm_v3,
        )

    async def tts_wrapped(state: ConversationState) -> ConversationState:
        return await text_to_speech_node(
            state,
            elevenlabs=elevenlabs_tts,
            openai_tts=openai_tts,
            catalog=voice_catalog,
            audit=audit,
        )

    async def dialogue_policy_wrapped(state: ConversationState) -> ConversationState:
        if dialogue_policy_node_fn is not None:
            return await dialogue_policy_node_fn(state)
        return await dialogue_policy_node(
            state, audit=audit, judge_llm=cbt_judge_llm,
        )

    async def understanding_wrapped(state: ConversationState) -> ConversationState:
        if understanding_synthesis_node_fn is not None:
            return await understanding_synthesis_node_fn(state)
        return await understanding_synthesis_node(
            state, audit=audit, llm=understanding_synthesis_llm,
        )

    async def memory_wrapped(state: ConversationState) -> ConversationState:
        if memory_retrieval_node_fn is not None:
            return await memory_retrieval_node_fn(state)
        return await memory_retrieval_node(
            state, context_builder=context_builder, audit=audit,
        )

    async def response_wrapped(state: ConversationState) -> ConversationState:
        if response_generator_node_fn is not None:
            return await response_generator_node_fn(state)
        return await response_generator_node(
            state,
            llm=response_llm,
            audit=audit,
            tools=response_tools,
            assessment_repo=assessment_repo,
        )

    async def session_end_wrapped(state: ConversationState) -> ConversationState:
        if session_end_node_fn is not None:
            return await session_end_node_fn(state)
        return await session_end_node(
            state, activity_repo=activity_repo, audit=audit,
        )

    async def input_guard_wrapped(state: ConversationState) -> ConversationState:
        return await input_guardrail_node(state, audit=audit)

    async def linguistic_wrapped(state: ConversationState) -> ConversationState:
        if linguistic_node is not None:
            return await linguistic_node(state)
        return await linguistic_enrichment_node(state, audit=audit)

    async def crisis_guard_wrapped(state: ConversationState) -> ConversationState:
        return await crisis_guardrail_node(state, audit=audit)

    async def crisis_triage_wrapped(
        state: ConversationState,
    ) -> ConversationState:
        return await crisis_triage_node(state, audit=audit)

    async def crisis_escalation_wrapped(
        state: ConversationState,
    ) -> ConversationState:
        return await crisis_escalation_node(state, audit=audit)

    async def crisis_empathy_wrapped(
        state: ConversationState,
    ) -> ConversationState:
        return await crisis_empathy_node(state, llm=crisis_empathy_llm, audit=audit)

    async def output_guard_wrapped(state: ConversationState) -> ConversationState:
        return await output_guardrail_node(
            state, audit=audit, rewrite_llm=rewrite_llm
        )

    async def phq9_check_wrapped(state: ConversationState) -> ConversationState:
        return await phq9_check_node(state, repo=assessment_repo)

    async def phq9_delivery_wrapped(state: ConversationState) -> ConversationState:
        return await phq9_delivery_node(
            state,
            repo=assessment_repo,
            judge_llm=phq9_judge_llm or scorer_llm,
            clarification_llm=phq9_clarification_llm,
            feedback_llm=feedback_llm,
            audit=audit,
        )

    g: Any = StateGraph(ConversationState)

    g.add_node("entry", audited_node("entry", _turn_init_node))
    g.add_node("speech_to_text", audited_node("speech_to_text", stt_wrapped))
    g.add_node("input_guardrail_node", audited_node("input_guardrail_node", input_guard_wrapped))
    g.add_node("linguistic_enrichment", audited_node("linguistic_enrichment", linguistic_wrapped))
    g.add_node("phq9_check", audited_node("phq9_check", phq9_check_wrapped))
    g.add_node("crisis_guardrail", audited_node("crisis_guardrail", crisis_guard_wrapped))
    g.add_node("memory_retrieval", audited_node("memory_retrieval", memory_wrapped))
    # v3 pipeline only (AXIS_RESPONSE_PIPELINE_VERSION=v3): node is not even
    # added to the graph on v2, so v2 pays zero extra latency/cost for it --
    # this keeps a v2-vs-v3 comparison an honest whole-pipeline comparison,
    # not a partial mix.
    response_pipeline_version = os.getenv("AXIS_RESPONSE_PIPELINE_VERSION", "v2").strip().lower()
    if response_pipeline_version == "v3":
        g.add_node(
            "understanding_synthesis",
            audited_node("understanding_synthesis", understanding_wrapped),
        )
    g.add_node("dialogue_policy", audited_node("dialogue_policy", dialogue_policy_wrapped))
    g.add_node("phq9_delivery", audited_node("phq9_delivery", phq9_delivery_wrapped))
    g.add_node("response_generator", audited_node("response_generator", response_wrapped))
    g.add_node("output_guardrail", audited_node("output_guardrail", output_guard_wrapped))
    # converge
    g.add_node("crisis_triage", audited_node("crisis_triage", crisis_triage_wrapped))
    g.add_node("crisis_escalation", audited_node("crisis_escalation", crisis_escalation_wrapped))
    g.add_node("crisis_empathy", audited_node("crisis_empathy", crisis_empathy_wrapped))
    g.add_node("speech_adapter", audited_node("speech_adapter", speech_adapter_wrapped))
    g.add_node("text_to_speech", audited_node("text_to_speech", tts_wrapped))
    g.add_node("session_end", audited_node("session_end", session_end_wrapped))

    g.set_entry_point("entry")
    g.add_conditional_edges(
        "entry",
        route_entry,
        {
            "speech_to_text": "speech_to_text",
            "input_guardrail_node": "input_guardrail_node",
        },
    )
    g.add_edge("speech_to_text", "input_guardrail_node")

    g.add_conditional_edges(
        "input_guardrail_node",
        route_after_input_guardrail,
        {
            "crisis_triage": "crisis_triage",
            "response_generator": "response_generator",
            "linguistic_enrichment": "linguistic_enrichment",
            "output_guardrail": "output_guardrail",
        },
    )
    g.add_edge("linguistic_enrichment", "phq9_check")
    g.add_edge("phq9_check", "crisis_guardrail")

    g.add_conditional_edges(
        "crisis_guardrail",
        route_after_crisis_check,
        {
            "crisis_triage": "crisis_triage",
            "memory_retrieval": "memory_retrieval",
        },
    )

    g.add_conditional_edges(
        "crisis_triage",
        route_after_crisis_triage,
        {
            "crisis_escalation": "crisis_escalation",
            "crisis_empathy": "crisis_empathy",
        },
    )

    if response_pipeline_version == "v3":
        g.add_edge("memory_retrieval", "understanding_synthesis")
        g.add_edge("understanding_synthesis", "dialogue_policy")
    else:
        g.add_edge("memory_retrieval", "dialogue_policy")

    g.add_conditional_edges(
        "dialogue_policy",
        route_after_dialogue,
        {
            "phq9_delivery": "phq9_delivery",
            "response_generator": "response_generator",
        },
    )

    g.add_conditional_edges(
        "phq9_delivery",
        route_after_phq9_delivery,
        {
            "response_generator": "response_generator",
            "output_guardrail": "output_guardrail",
        },
    )
    g.add_edge("response_generator", "output_guardrail")

    g.add_node("post_guardrail_router", audited_node("post_guardrail_router", _noop_node))
    g.add_conditional_edges(
        "output_guardrail",
        route_after_output_guardrail,
        {
            "crisis_triage": "crisis_triage",
            "crisis_escalation": "crisis_escalation",
            "session_end": "post_guardrail_router",
        },
    )

    g.add_edge("crisis_escalation", "post_guardrail_router")
    g.add_edge("crisis_empathy", "post_guardrail_router")

    g.add_conditional_edges(
        "post_guardrail_router",
        route_after_output_finalized,
        {
            "speech_adapter": "speech_adapter",
            "session_end": "session_end",
        },
    )

    g.add_edge("speech_adapter", "text_to_speech")
    g.add_edge("text_to_speech", "session_end")
    g.add_edge("session_end", END)

    return g.compile()


async def _noop_node(state: ConversationState) -> ConversationState:
    """pass"""
    return state


__all__ = [
    "build_graph",
    "route_entry",
    "route_after_input_guardrail",
    "route_after_crisis_check",
    "route_after_dialogue",
    "route_after_output_guardrail",
    "route_after_output_finalized",
    "route_after_crisis_triage",
]

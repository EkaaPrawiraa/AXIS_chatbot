"""wiring."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from agentic.agent.audit.guardrail_events import (
    GuardrailLogger,
    NullGuardrailLogger,
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


async def _load_profile_context(user_id: str) -> dict[str, str | None] | None:
    """load fields"""
    try:
        from agentic.memory.pg_vector.client import get_pool  # noqa: PLC0415

        pool = await get_pool()
        if not pool:
            return None
        row = await pool.fetchrow(
            """
            SELECT display_name, preferred_language, gender
            FROM users
            WHERE id = $1::uuid
            """,
            user_id,
        )
        if not row:
            return None
        context: dict[str, str | None] = {
            "display_name": row["display_name"],
            "preferred_language": row["preferred_language"],
            "gender": row["gender"],
        }
        mood_context = await _load_mood_context(pool, user_id)
        if mood_context:
            context.update(mood_context)
        return context
    except Exception as exc:  # pragma: no cover
        logger.warning("_load_profile_context failed: %s", exc)
        return None


async def _load_mood_context(pool: Any, user_id: str) -> dict[str, str | None] | None:
    """load mood & trend"""
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
    """clear transients"""
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

    # sync fields into db on first turn
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
    """voice or text turn"""
    voice = state.get("voice_state") or {}
    if voice.get("audio_input") is not None:
        return "speech_to_text"
    return "input_guardrail_node"


def route_after_input_guardrail(state: ConversationState) -> str:
    """route guardrail"""
    verdict = state.get("input_guardrail") or {}
    decision = verdict.get("decision")
    reason = verdict.get("reason", "")
    if decision == "escalate_crisis":
        return "crisis_triage"
    if decision == "block":
        if reason == "off_scope":
            # skip llm, pass to voice/sesend
            return "output_guardrail"
        return "response_generator"  # jailbreak: let LLM compose a safe refusal
    return "linguistic_enrichment"


def route_after_output_finalized(state: ConversationState) -> str:
    """voice out when req'd."""
    voice = state.get("voice_state") or {}
    if voice.get("output_modality") in ("voice", "both"):
        return "speech_adapter"
    return "session_end"


def route_after_crisis_check(state: ConversationState) -> str:
    """route l3 pre-gen"""
    if state.get("safety_flag") == "crisis":
        return "crisis_triage"
    return "memory_retrieval"


def route_after_dialogue(state: ConversationState) -> str:
    """route to node"""
    phq9 = state.get("phq9_state") or {}
    phase = phq9.get("phase", "idle")
    if phase == "offer_pending":
        return "response_generator"
    if phase in ("offered", "in_progress", "awaiting_clar"):
        return "phq9_delivery"
    return "response_generator"


def route_after_phq9_delivery(state: ConversationState) -> str:
    """`skip offer decl`"""
    if state.get("phq9_declined_note") and not state.get("response_draft"):
        return "response_generator"
    return "output_guardrail"


def route_after_output_guardrail(state: ConversationState) -> str:
    """safety outcomes."""
    phq9 = state.get("phq9_state") or {}
    if state.get("safety_flag") in ("crisis", "escalate"):
        return "crisis_triage"
    if phq9.get("route_to_crisis_after"):
        return "crisis_triage"
    return "session_end"


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
) -> Any:
    """build & compile LangGraph DAG"""
    from langgraph.graph import END, StateGraph

    audit = audit_logger or NullGuardrailLogger()

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

    g.add_node("entry", _turn_init_node)
    g.add_node("speech_to_text", stt_wrapped)
    g.add_node("input_guardrail_node", input_guard_wrapped)
    g.add_node("linguistic_enrichment", linguistic_wrapped)
    g.add_node("phq9_check", phq9_check_wrapped)
    g.add_node("crisis_guardrail", crisis_guard_wrapped)
    g.add_node("memory_retrieval", memory_wrapped)
    g.add_node("dialogue_policy", dialogue_policy_wrapped)
    g.add_node("phq9_delivery", phq9_delivery_wrapped)
    g.add_node("response_generator", response_wrapped)
    g.add_node("output_guardrail", output_guard_wrapped)
    # converge end
    g.add_node("crisis_triage", crisis_triage_wrapped)
    g.add_node("crisis_escalation", crisis_escalation_wrapped)
    g.add_node("crisis_empathy", crisis_empathy_wrapped)
    g.add_node("speech_adapter", speech_adapter_wrapped)
    g.add_node("text_to_speech", tts_wrapped)
    g.add_node("session_end", session_end_wrapped)

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

    g.add_node("post_guardrail_router", _noop_node)
    g.add_conditional_edges(
        "output_guardrail",
        route_after_output_guardrail,
        {
            "crisis_triage": "crisis_triage",
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
    """`pass`"""
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

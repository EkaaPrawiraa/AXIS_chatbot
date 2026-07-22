"""understand_synthesis: silent, v3, mentalization, CBT, trauma, response_generator, translate."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.state import ConversationState
from agentic.config.llm_models import UNDERSTANDING_SYNTHESIS, build_llm
from agentic.gateway.monitoring import observe_langchain_usage


logger = logging.getLogger(__name__)


try:  # pragma: no cover
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover

    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"


@dataclass(frozen=True)
class UnderstandingSynthesis:
    """understand_synthesis."""

    current_emotion: str | None
    unmet_need: str | None
    active_pattern: str | None
    grounding_experience: str | None
    possible_explanations: tuple[dict[str, Any], ...]
    triggering_pattern: str | None
    unspoken_undercurrent: str | None
    response_guidance: str | None
    insufficient_data: bool
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_emotion": self.current_emotion,
            "unmet_need": self.unmet_need,
            "active_pattern": self.active_pattern,
            "grounding_experience": self.grounding_experience,
            "possible_explanations": list(self.possible_explanations),
            "triggering_pattern": self.triggering_pattern,
            "unspoken_undercurrent": self.unspoken_undercurrent,
            "response_guidance": self.response_guidance,
            "insufficient_data": self.insufficient_data,
        }


def _insufficient_data_result(raw: str = "") -> UnderstandingSynthesis:
    return UnderstandingSynthesis(
        current_emotion=None,
        unmet_need=None,
        active_pattern=None,
        grounding_experience=None,
        possible_explanations=(),
        triggering_pattern=None,
        unspoken_undercurrent=None,
        response_guidance=None,
        insufficient_data=True,
        raw=raw,
    )


_USER_TEMPLATE = (
    "Current user message:\n\"\"\"\n{message}\n\"\"\"\n\n"
    "[Memory Context]\n{kg_context}\n\n"
    "{synthesis_only_context}\n\n"
    "Linguistic signals: {linguistic_signals}\n\n"
    "Mood context: {mood_context}\n\n"
    "Respond with the JSON object only."
)


def _format_linguistic_signals(signals: dict[str, Any] | None) -> str:
    if not signals:
        return "(unavailable)"
    parts: list[str] = []
    register = signals.get("register")
    if register:
        parts.append(f"register={register}")
    distress_terms = signals.get("distress_terms") or []
    if distress_terms:
        parts.append(f"distress_terms={','.join(distress_terms[:5])}")
    return ", ".join(parts) if parts else "(no signal)"


def _format_mood_context(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return "(unavailable)"
    parts: list[str] = []
    mood_today = profile.get("mood_today_score")
    mood_trend = profile.get("mood_trend")
    if mood_today:
        parts.append(f"today={mood_today}")
    if mood_trend:
        parts.append(f"trend={mood_trend}")
    return ", ".join(parts) if parts else "(unavailable)"


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _str_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_synthesis_output(raw: str) -> UnderstandingSynthesis:
    if not raw:
        logger.warning("understanding_synthesis empty output")
        return _insufficient_data_result(raw)

    match = _JSON_RE.search(raw)
    payload = match.group(0) if match else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("understanding_synthesis non-json: %r", raw[:200])
        return _insufficient_data_result(raw)

    if not isinstance(data, dict):
        return _insufficient_data_result(raw)

    explanations_raw = data.get("possible_explanations")
    explanations: list[dict[str, Any]] = []
    if isinstance(explanations_raw, list):
        for item in explanations_raw:
            if not isinstance(item, dict):
                continue
            hypothesis = _str_or_none(item.get("hypothesis"))
            if hypothesis is None:
                continue
            weight = item.get("weight")
            explanations.append(
                {
                    "hypothesis": hypothesis,
                    "weight": weight if isinstance(weight, (int, float)) else None,
                }
            )

    return UnderstandingSynthesis(
        current_emotion=_str_or_none(data.get("current_emotion")),
        unmet_need=_str_or_none(data.get("unmet_need")),
        active_pattern=_str_or_none(data.get("active_pattern")),
        grounding_experience=_str_or_none(data.get("grounding_experience")),
        possible_explanations=tuple(explanations),
        triggering_pattern=_str_or_none(data.get("triggering_pattern")),
        unspoken_undercurrent=_str_or_none(data.get("unspoken_undercurrent")),
        response_guidance=_str_or_none(data.get("response_guidance")),
        insufficient_data=bool(data.get("insufficient_data", False)),
        raw=raw,
    )


async def _fetch_thought_record_history(user_id: str, *, limit: int = 3) -> list[dict[str, Any]]:
    """`skip`"""
    try:
        from agentic.memory.neo4j_client import get_client

        rows = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[rel:HAS_THOUGHT_RECORD]->(tr:ThoughtRecord)
            WHERE rel.t_invalid IS NULL
            RETURN tr.thought AS thought, tr.distortion AS distortion, tr.balanced AS balanced
            ORDER BY tr.recorded_at DESC
            LIMIT $limit
            """,
            {"user_id": user_id, "limit": limit},
        )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("thought_record_history fetch failed (user=%s): %s", user_id, exc)
        return []


async def _fetch_phq9_snapshot(user_id: str) -> Any | None:
    """already existed; never consulted."""
    try:
        from agentic.memory.assessment_repo import AssessmentRepository
        from agentic.memory.pg_vector.client import get_pool

        pool = await get_pool()
        if pool is None:
            return None
        repo = AssessmentRepository(pg_pool=pool)
        return await repo.get_last_phq9(user_id)
    except Exception as exc:
        logger.warning("phq9 snapshot fetch failed (user=%s): %s", user_id, exc)
        return None


async def build_synthesis_only_context(user_id: str) -> str:
    if not user_id:
        return ""

    records, phq9 = await asyncio.gather(
        _fetch_thought_record_history(user_id),
        _fetch_phq9_snapshot(user_id),
    )

    lines: list[str] = []
    thought_record_lines: list[str] = []
    for r in records:
        thought = (r.get("thought") or "").strip()
        if not thought:
            continue
        piece = f'  - "{thought}"'
        distortion = (r.get("distortion") or "").strip()
        if distortion:
            piece += f" [{distortion}]"
        balanced = (r.get("balanced") or "").strip()
        if balanced:
            piece += f' -> balanced thought reached: "{balanced}"'
        thought_record_lines.append(piece)

    if thought_record_lines or phq9 is not None:
        lines.append("[CBT & Assessment History -- internal only]")
    if thought_record_lines:
        lines.append("Thought records (distortions already worked on, and the balanced thought reached):")
        lines.extend(thought_record_lines)

    if phq9 is not None:
        trend = "unknown"
        if phq9.delta_from_prev is not None:
            if phq9.delta_from_prev > 0:
                trend = "worsening"
            elif phq9.delta_from_prev < 0:
                trend = "improving"
            else:
                trend = "stable"
        lines.append(
            f"PHQ-9: severity={phq9.severity.value}, trend={trend}, "
            f"administered_at={phq9.administered_at.isoformat()}"
        )

    return "\n".join(lines)


def _build_default_client() -> Any | None:
    try:
        return build_llm(UNDERSTANDING_SYNTHESIS)
    except Exception as exc:  # pragma: no cover defensive
        logger.warning("understanding_synthesis build_llm failed: %s", exc)
        return None


async def synthesize_understanding(
    state: ConversationState,
    *,
    llm: Any | None = None,
) -> UnderstandingSynthesis:
    """Run one understanding_synthesis pass."""
    kg_context = (state.get("kg_context") or "").strip()
    synthesis_only_context = await build_synthesis_only_context(state.get("user_id") or "")
    if not kg_context and not synthesis_only_context:
        # `skip`
        return _insufficient_data_result()

    client = llm if llm is not None else _build_default_client()
    if client is None:
        return _insufficient_data_result()

    user_prompt = _USER_TEMPLATE.format(
        message=(state.get("current_message") or "").strip() or "(empty)",
        kg_context=kg_context or "(empty)",
        synthesis_only_context=synthesis_only_context,
        linguistic_signals=_format_linguistic_signals(state.get("linguistic_signals")),
        mood_context=_format_mood_context(state.get("profile_context")),
    )

    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=UNDERSTANDING_SYNTHESIS.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        observe_langchain_usage(ai, fallback_model=UNDERSTANDING_SYNTHESIS.model)
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
    except Exception as exc:  # pragma: no cover defensive
        logger.warning("understanding_synthesis call failed: %s", exc)
        return _insufficient_data_result()

    return _parse_synthesis_output(raw)


async def understanding_synthesis_node(
    state: ConversationState,
    *,
    llm: Any | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    audit = audit or NullGuardrailLogger()
    started = time.perf_counter()

    result = await synthesize_understanding(state, llm=llm)
    state["user_understanding"] = result.to_dict()  # type: ignore[typeddict-item]

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,  # closest existing layer label
            event_type="understanding_synthesis",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=(
                "insufficient_data" if result.insufficient_data else "synthesized"
            ),
            latency_ms=elapsed_ms,
            metadata={"result": result.to_dict()},
        )
    )
    return state


__all__ = [
    "UnderstandingSynthesis",
    "build_synthesis_only_context",
    "synthesize_understanding",
    "understanding_synthesis_node",
]

"""buat nyimpen"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from agentic.agent.session.finalizer import (
    HistoryLoader,
    KGExtractorFn,
    KGWriterFn,
    SessionFinalizer,
    SessionMetadataLoaderFn,
    SummarizerFn,
    UserContextLoaderFn,
)
from agentic.config.llm_models import KG_EXTRACTOR, SESSION_SUMMARIZER, build_llm
from agentic.gateway.monitoring import observe_langchain_usage

logger = logging.getLogger(__name__)


def _strip_thinking(text: str) -> str:
    """rm <think>...</think>"""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


_KG_JSON_SCHEMA = """
Return a JSON object with the keys below. Omit any key that has no
facts to report. Numbers are floats in the declared ranges. Never
invent facts; use the user's own wording for description/content fields.

Node arrays use 0-based indexing. The "relations" object references
those indices to describe which nodes are connected. For example,
experience_to_emotion: [[0, 1]] means experiences[0] triggered emotions[1].

{
  "thoughts": [
    {
      "content":       "<automatic thought verbatim or paraphrased>",
      "thought_type":  "<automatic|core_belief|intermediate>",
      "distortion":    "<catastrophizing|mind_reading|all_or_nothing|fortune_telling|emotional_reasoning|should_statements|labeling|magnification|personalization|overgeneralization|null>",
      "believability":  <float 0.0-1.0>,
      "supersedes_thought_id": "<existing Thought.id only when this explicitly reframes or corrects it, otherwise null>",
      "supersedes_reason": "<user_reframe|cbt_reframe|null>"
    }
  ],
  "emotions": [
    {
      "label":       "<anxious|sad|angry|ashamed|hopeful|grateful|...>",
      "intensity":    <float 0.0-1.0>,
      "valence":      <float -1.0 to 1.0>,
      "source_text":  "<verbatim or near-verbatim user phrase>"
    }
  ],
  "experiences": [
    {
      "description":  "<what happened, concrete situation>",
      "occurred_at":  "<ISO datetime, approximate if unknown>",
      "valence":       <float -1.0 to 1.0>,
      "significance":  <float 0.0-1.0>,
      "reappraises_experience_id": "<existing Experience.id only when the user explicitly gives a new meaning to that same experience, otherwise null>",
      "reappraisal_reason": "<user_reappraisal|meaning_update|null>"
    }
  ],
  "triggers": [
    {
      "category":    "<academic|social|family|organizational|career|financial|housing|health|work|other>",
      "description": "<concise trigger label>",
      "significance": <float 0.0-1.0>
    }
  ],
  "trigger_updates": [
    {
      "trigger_id": "<existing Trigger.id only when the user clearly says this trigger is resolved/no longer active>",
      "action":     "<deactivate>",
      "reason":     "<resolved|no_longer_relevant|user_reported_safe>"
    }
  ],
  "behaviors": [
    {
      "description": "<what the user did>",
      "category":    "<avoidance|rumination|exercise|substance_use|social_withdrawal|help_seeking|other>",
      "adaptive":     <true|false>,
      "significance": <float 0.0-1.0>,
      "replaces_behavior_id": "<existing Behavior.id only when this behavior clearly replaces an older behavior, otherwise null>",
      "replacement_reason": "<healthier_coping|user_changed_strategy|null>"
    }
  ],
  "subjects": [
    {
      "name":                 "<exact name or pronoun the user used>",
      "role":                 "<friend|parent|partner|sibling|professor|colleague|therapist|thesis_advisor|academic_advisor|boarding_house_manager|roommate|org_senior|groupmate|other>",
      "subject_type":          "<person|pet|object|place|other>",
      "sentiment":             <float -1.0 to 1.0>,
      "relationship_quality": "<supportive|complicated|negative|neutral>"
    }
  ],
  "topics": [
    {
      "name":      "<concise snake_case label, e.g. academic-stress, relationship-conflict>",
      "category":  "<academic|social|family|organizational|career|health|financial|identity|mental_health|other>",
      "sentiment":  <float -1.0 to 1.0>
    }
  ],
  "relations": {
    "experience_to_trigger":  [[<exp_idx>, <trig_idx>], ...],
    "experience_to_emotion":  [[<exp_idx>, <emo_idx>], ...],
    "experience_to_subject":  [[<exp_idx>, <subj_idx>], ...],
    "experience_to_topic":   [[<exp_idx>, <topic_idx>], ...],
    "emotion_to_thought":    [[<emo_idx>, <thought_idx>], ...],
    "emotion_to_behavior":   [[<emo_idx>, <beh_idx>], ...],
    "emotion_to_topic":      [[<emo_idx>, <topic_idx>], ...],
    "thought_to_behavior":   [[<thought_idx>, <beh_idx>], ...],
    "thought_to_topic":      [[<thought_idx>, <topic_idx>], ...]
  }
}
"""


_KG_FACT_COUNT_KEYS = (
    "thoughts",
    "emotions",
    "experiences",
    "triggers",
    "trigger_updates",
    "behaviors",
    "subjects",
    "topics",
)


def _count_fact_items(fact: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in _KG_FACT_COUNT_KEYS:
        value = fact.get(key)
        counts[key] = len(value) if isinstance(value, list) else 0
    relations = fact.get("relations")
    counts["relations"] = (
        sum(len(value) for value in relations.values() if isinstance(value, list))
        if isinstance(relations, Mapping)
        else 0
    )
    return counts


def _safe_iso_datetime(value: Any, *, fallback: str) -> str:
    """extractor sometimes returns a non-ISO placeholder (e.g. 'UNKNOWN') instead
    of an approximate date; Neo4j's datetime() rejects that outright, so validate
    before it ever reaches Cypher rather than losing the whole node to a write error"""
    if isinstance(value, str) and value.strip():
        try:
            datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return value.strip()
        except ValueError:
            logger.warning("Discarding non-ISO occurred_at from extractor: %r", value)
    return fallback


def _clean_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"null", "none"}:
            return None
        return stripped
    return str(value).strip() or None


def _source_message_id(fact: Mapping[str, Any]) -> str | None:
    return _clean_optional_str(fact.get("__source_message_id"))


def _supersede_reason(value: Any) -> str:
    reason = _clean_optional_str(value)
    if reason in {"user_reframe", "cbt_reframe", "therapist_note"}:
        return reason
    return "user_reframe"


def _lifecycle_reason(value: Any, default: str) -> str:
    reason = _clean_optional_str(value)
    if reason:
        return reason[:80]
    return default


_CONTROL_MEMORY_PATTERNS = (
    r"\bdebug\b",
    r"\btest(?:ing)?\b",
    r"\btes\s+(?:mood|suasana hati|phq|fitur|chip|button)\b",
    r"\bphq[-\s]?9\b",
    r"\bkuesioner\b",
    r"\bapa yang (?:kamu|axis) ingat\b",
    r"\bapa saja yang .*cerita(?:kan)?(?: sebelumnya)?\b",
    r"\bpernah .*cerita(?:kan)? sebelumnya\b",
    r"\b(?:asisten|assistant|axis).*(?:mengingat|remembered|ingatkan)\b",
    r"\b(?:asisten|assistant|axis).*(?:bisa apa|kemampuan|mampu)\b",
    r"\bobrolan sebelumnya\b",
    r"\b(?:suara|voice).*(?:kedengeran|terdengar|masuk)\b",
    r"\b(?:nggak|gak|ga|tidak) ada hal spesifik\b",
    r"\bbelum ada peristiwa\b",
    r"\bmenyapa (?:dengan )?(?:ringan|santai)\b",
    r"\bsotoy\b",
    r"\b(?:film|movie|rekomendasi|rekomendasikan)\b",
    r"\b(?:nebak|tebak|nyanyi|lagu|song)\b",
    r"\b(?:buat|bikin|bikinin).*\b(?:teks|caption|tren|trend)\b",
    r"\bdevil couldn.?t reach me\b",
    r"\b(?:terangsang|eksplisit|18\\+|seksual)\b",
    r"\bskor depresi\b",
    r"\b(?:frontend|backend|database|localhost|ui|bug|error)\b",
)

_LOW_VALUE_TOPIC_NAMES = {
    "tes_mood",
    "mood_test",
    "phq9",
    "phq_9",
    "questionnaire",
    "kuesioner",
    "axis",
    "chatbot",
    "app_testing",
    "debug",
    "mental_health",  # too broad; use self_worth/social_isolation/etc. instead
}


def _lower_compact(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _is_control_memory_text(value: Any) -> bool:
    text = _lower_compact(value)
    if not text:
        return True
    return any(re.search(pattern, text) for pattern in _CONTROL_MEMORY_PATTERNS)


def _fact_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _should_write_experience(item: Mapping[str, Any]) -> bool:
    description = _lower_compact(item.get("description"))
    if not description or _is_control_memory_text(description):
        return False
    significance = _fact_float(item.get("significance"), 0.0)
    valence = abs(_fact_float(item.get("valence"), 0.0))
    # skip mild events
    return significance >= 0.45 or (significance >= 0.35 and valence >= 0.65)


def _should_write_thought(item: Mapping[str, Any]) -> bool:
    content = _lower_compact(item.get("content"))
    if not content or _is_control_memory_text(content):
        return False
    # skip long-term
    if len(content) < 16 and not re.search(r"\b(?:aku|saya|teman|orang|keluarga)\b", content):
        return False
    # skip ltm
    believability = _fact_float(item.get("believability"), 0.5)
    return believability >= 0.3


def _should_write_trigger(item: Mapping[str, Any]) -> bool:
    description = _lower_compact(item.get("description"))
    if not description or _is_control_memory_text(description):
        return False
    if len(description) < 8:
        return False
    significance = _fact_float(item.get("significance"), 0.5)
    return significance >= 0.4


def _should_write_emotion(item: Mapping[str, Any]) -> bool:
    label = _lower_compact(item.get("label"))
    source_text = _lower_compact(item.get("source_text"))
    if not label or not source_text or _is_control_memory_text(source_text):
        return False
    intensity = _fact_float(item.get("intensity"), 0.5)
    return intensity >= 0.4


def _should_write_behavior(item: Mapping[str, Any]) -> bool:
    description = _lower_compact(item.get("description"))
    if not description or _is_control_memory_text(description):
        return False
    significance = _fact_float(item.get("significance"), 0.5)
    return significance >= 0.4


def _should_write_topic(item: Mapping[str, Any]) -> bool:
    name = _lower_compact(item.get("name")).replace("-", "_")
    if not name or name in _LOW_VALUE_TOPIC_NAMES:
        return False
    if _is_control_memory_text(name):
        return False
    return True


def _summary_importance(summary: str, extracted: Sequence[Mapping[str, Any]]) -> float:
    text = _lower_compact(summary)
    if not text or text == "{}" or _is_control_memory_text(text):
        return 0.0

    importance = 0.52
    for fact in extracted:
        for item in fact.get("experiences") or []:
            importance = max(importance, _fact_float(item.get("significance"), 0.0))
        for item in fact.get("emotions") or []:
            importance = max(importance, abs(_fact_float(item.get("valence"), 0.0)) * 0.75)
        for item in fact.get("thoughts") or []:
            importance = max(importance, _fact_float(item.get("believability"), 0.0) * 0.8)
    return min(max(importance, 0.0), 0.9)


def make_history_loader() -> HistoryLoader:
    """load_from_postgres"""

    async def _loader(
        *,
        session_id: str,
        user_id: str,
        after_turn_index: int | None = None,
        through_turn_index: int | None = None,
    ) -> Sequence[Mapping[str, Any]]:
        from agentic.memory.pg_vector.client import get_pool

        pool = await get_pool()
        if pool is None:
            logger.warning(
                "history_loader: Postgres pool unavailable (session=%s)",
                session_id,
            )
            return []

        params: list[Any] = [session_id]
        filters = ["session_id = $1"]
        if after_turn_index is not None:
            params.append(after_turn_index)
            filters.append(f"turn_index >= ${len(params)}")
        if through_turn_index is not None:
            params.append(through_turn_index)
            filters.append(f"turn_index <= ${len(params)}")

        sql = (
            "SELECT id::text AS id, role, content, turn_index, metadata "
            "FROM messages "
            f"WHERE {' AND '.join(filters)} "
            "ORDER BY turn_index ASC"
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [dict(r) for r in rows]

    return _loader  # type: ignore[return-value]


def make_session_metadata_loader() -> SessionMetadataLoaderFn:
    """load sess. safely."""

    async def _meta_loader(
        *, session_id: str, user_id: str,
    ) -> dict:
        from agentic.memory.pg_vector.client import get_pool

        pool = await get_pool()
        if pool is None:
            logger.warning("session_metadata_loader: Postgres pool unavailable")
            return {}

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT started_at, channel, turn_count,
                       sentiment_avg, safety_escalated
                FROM chat_sessions
                WHERE id = $1::uuid AND user_id = $2::uuid
                """,
                session_id, user_id,
            )

        if not row:
            logger.warning(
                "session_metadata_loader: session %s not found in Postgres",
                session_id,
            )
            return {}

        return {
            "started_at":       row["started_at"].isoformat() if row["started_at"] else None,
            "channel":          row["channel"],
            "turn_count":       row["turn_count"],
            "sentiment_avg":    row["sentiment_avg"],
            "safety_escalated": row["safety_escalated"],
        }

    return _meta_loader  # type: ignore[return-value]


def make_user_context_loader() -> UserContextLoaderFn:
    """load safe cross-session KG"""

    async def _ctx_loader(*, user_id: str) -> dict:
        try:
            from agentic.memory.knowledge_graph.kg_retriever.signals import (
                fetch_active_behaviors,
                fetch_active_distortions,
                fetch_recent_experiences,
                fetch_recurring_themes,
                fetch_recurring_triggers,
            )
            from agentic.memory.neo4j_client import get_client
        except Exception as exc:
            logger.warning("user_context_loader: import failed: %s", exc)
            return {}

        try:
            persons_raw = await get_client().execute_read(
                """
                MATCH (u:User {id: $user_id})-[:HAS_SUBJECT]->(p:Subject)
                RETURN p.name       AS name,
                       p.role       AS role,
                       p.sentiment  AS sentiment
                ORDER BY p.mention_count DESC
                LIMIT 5
                """,
                {"user_id": user_id},
            )
            thoughts_raw = await fetch_active_distortions(user_id, limit=5)
            themes_raw  = await fetch_recurring_themes(user_id, limit=5)
            triggers_raw = await fetch_recurring_triggers(user_id, limit=3)
            experiences_raw = await fetch_recent_experiences(user_id, limit=5)
            behaviors_raw = await fetch_active_behaviors(user_id, limit=5)
        except Exception as exc:
            logger.warning(
                "user_context_loader: Neo4j query failed (user=%s): %s",
                user_id, exc,
            )
            return {}

        return {
            "known_subjects":    [dict(r) for r in (persons_raw  or [])],
            "active_thoughts":   [dict(r) for r in (thoughts_raw or [])],
            "recurring_themes": [dict(r) for r in (themes_raw   or [])],
            "active_triggers":  [dict(r) for r in (triggers_raw or [])],
            "recent_experiences": [dict(r) for r in (experiences_raw or [])],
            "active_behaviors": [dict(r) for r in (behaviors_raw or [])],
        }

    return _ctx_loader  # type: ignore[return-value]


def make_summarizer() -> SummarizerFn:
    """build summary fn"""

    async def _summarizer(
        *,
        transcript: str,
        language: str | None,
        session_metadata: Mapping[str, Any] | None = None,
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = build_llm(SESSION_SUMMARIZER)
        messages: list[Any] = [SystemMessage(content=SESSION_SUMMARIZER.system_prompt)]
        if language:
            messages.append(SystemMessage(content=f"Respond in {language}."))

        if session_metadata:
            meta_lines: list[str] = ["[Session metadata]"]
            if session_metadata.get("started_at"):
                meta_lines.append(f"  started_at: {session_metadata['started_at']}")
            if session_metadata.get("channel"):
                meta_lines.append(f"  channel: {session_metadata['channel']}")
            if session_metadata.get("turn_count") is not None:
                meta_lines.append(f"  turn_count: {session_metadata['turn_count']}")
            if session_metadata.get("sentiment_avg") is not None:
                meta_lines.append(f"  sentiment_avg: {session_metadata['sentiment_avg']:.2f}")
            if session_metadata.get("safety_escalated"):
                meta_lines.append("  safety_escalated: true")
            messages.append(SystemMessage(content="\n".join(meta_lines)))

        messages.append(HumanMessage(content=transcript))

        response = await llm.ainvoke(messages)
        observe_langchain_usage(response, fallback_model=SESSION_SUMMARIZER.model)
        return (response.content or "").strip()

    return _summarizer  # type: ignore[return-value]


def make_kg_extractor() -> KGExtractorFn:
    """safe_extraction()"""

    async def _extractor(
        *,
        message: str,
        user_id: str,
        session_id: str,
        language: str | None,
        preceding_context: list[dict[str, str]] | None = None,
        session_metadata: Mapping[str, Any] | None = None,
        user_kg_context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        llm = build_llm(KG_EXTRACTOR)
        system_text = KG_EXTRACTOR.system_prompt + "\n\nSchema:\n" + _KG_JSON_SCHEMA
        msgs: list[Any] = [SystemMessage(content=system_text)]
        if language:
            msgs.append(
                SystemMessage(
                    content=f"All text fields in the JSON must be in {language}."
                )
            )

        if session_metadata:
            meta_parts: list[str] = ["[Session context]"]
            if session_metadata.get("started_at"):
                meta_parts.append(f"  session_started_at: {session_metadata['started_at']}")
            if session_metadata.get("channel"):
                meta_parts.append(f"  channel: {session_metadata['channel']}")
            if session_metadata.get("safety_escalated"):
                meta_parts.append("  safety_escalated: true")
            msgs.append(SystemMessage(content="\n".join(meta_parts)))

        if user_kg_context:
            ctx_parts: list[str] = ["[Known user context from previous sessions]"]

            subjects = user_kg_context.get("known_subjects") or user_kg_context.get("known_persons") or []
            if subjects:
                ctx_parts.append("  Known subjects in user's life (people, pets, objects, places):")
                for p in subjects:
                    sentiment_str = f"{p.get('sentiment', 0.0):+.1f}" if p.get("sentiment") is not None else "?"
                    ctx_parts.append(f"    - {p.get('name', '?')} ({p.get('role', '?')}, sentiment {sentiment_str})")

            themes = user_kg_context.get("recurring_themes") or []
            if themes:
                ctx_parts.append("  Recurring themes already in KG (use these exact names when relevant):")
                for t in themes:
                    ctx_parts.append(f"    - {t.get('topic', '?')} (mentioned {t.get('times_reinforced', '?')}x)")

            triggers = user_kg_context.get("active_triggers") or []
            if triggers:
                ctx_parts.append("  Active recurring triggers (use id only if user clearly says one is resolved):")
                for tr in triggers:
                    ctx_parts.append(
                        f"    - id={tr.get('id', '?')} [{tr.get('category', '?')}] {tr.get('description', '?')} "
                        f"(freq {tr.get('frequency', '?')})"
                    )

            experiences = user_kg_context.get("recent_experiences") or []
            if experiences:
                ctx_parts.append("  Recent experiences that can receive a new reappraisal:")
                for ex in experiences:
                    ctx_parts.append(
                        f"    - id={ex.get('id', '?')}: {ex.get('description', '?')}"
                    )

            behaviors = user_kg_context.get("active_behaviors") or []
            if behaviors:
                ctx_parts.append("  Active behaviors that may be replaced by newer coping:")
                for beh in behaviors:
                    ctx_parts.append(
                        f"    - id={beh.get('id', '?')} [{beh.get('category', '?')}] "
                        f"{beh.get('description', '?')}"
                    )

            thoughts = user_kg_context.get("active_thoughts") or []
            if thoughts:
                ctx_parts.append("  Active unchallenged thoughts that may be reframed:")
                for th in thoughts:
                    believability = th.get("believability")
                    believability_str = f"{believability:.2f}" if believability is not None else "?"
                    ctx_parts.append(
                        f"    - id={th.get('id', '?')} "
                        f"distortion={th.get('distortion', '?')} "
                        f"belief={believability_str}: {th.get('content', '?')}"
                    )

            if len(ctx_parts) > 1:
                msgs.append(SystemMessage(content="\n".join(ctx_parts)))

        if preceding_context:
            for ctx_msg in preceding_context:
                ctx_role = ctx_msg.get("role")
                ctx_content = (ctx_msg.get("content") or "").strip()
                if not ctx_content:
                    continue
                if ctx_role == "assistant":
                    msgs.append(AIMessage(content=ctx_content))
                elif ctx_role == "user":
                    msgs.append(HumanMessage(content=ctx_content))
        msgs.append(HumanMessage(content=message))

        response = await llm.ainvoke(msgs)
        observe_langchain_usage(response, fallback_model=KG_EXTRACTOR.model)
        raw = _strip_thinking((response.content or "").strip())

        if raw.startswith("```"):
            _, _, rest = raw.partition("```")
            if rest.startswith("json"):
                rest = rest[4:]
            raw = rest.rstrip("`").strip()

        if not raw:
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "kg_extractor: JSON parse error (user=%s session=%s): %s",
                user_id, session_id, exc,
            )
            return {}

        if not isinstance(parsed, dict):
            return {}

        counts = _count_fact_items(parsed)
        logger.info(
            "kg_extractor counts user=%s session=%s thoughts=%d emotions=%d "
            "experiences=%d triggers=%d behaviors=%d subjects=%d topics=%d relations=%d",
            user_id,
            session_id,
            counts["thoughts"],
            counts["emotions"],
            counts["experiences"],
            counts["triggers"],
            counts["behaviors"],
            counts["subjects"],
            counts["topics"],
            counts["relations"],
        )
        return parsed

    return _extractor  # type: ignore[return-value]


def make_kg_writer() -> KGWriterFn:
    """write mem, extract kg, safe rel"""

    async def _ensure_kg_anchors(user_id: str, session_id: str) -> None:
        """ensure anchors" before "writes"""
        from agentic.memory.knowledge_graph.kg_writer import ensure_user_node
        from agentic.memory.neo4j_client import get_client
        from agentic.memory.pg_vector.client import get_pool

        pool = await get_pool()
        if pool:
            await ensure_user_node(user_id=user_id, pg_pool=pool)
        else:
            await get_client().execute_write(
                """
                MERGE (u:User {id: $user_id})
                ON CREATE SET
                    u.created_at  = datetime(),
                    u.last_active = datetime(),
                    u.session_count = 0,
                    u.onboarding_complete = false,
                    u.active = true
                ON MATCH SET
                    u.last_active = datetime()
                """,
                {"user_id": user_id},
            )

        await get_client().execute_write(
            """
            MERGE (s:Session {id: $session_id})
            ON CREATE SET
                s.started_at        = datetime(),
                s.ended_at          = null,
                s.channel           = 'text',
                s.summary           = null,
                s.sentiment_avg     = null,
                s.phq9_administered = false,
                s.created_by_sweeper = true
            WITH s
            MATCH (u:User {id: $user_id})
            MERGE (u)-[:HAD_SESSION {source_session: $session_id}]->(s)
            ON CREATE SET
                u.session_count = coalesce(u.session_count, 0) + 1
            """,
            {"user_id": user_id, "session_id": session_id},
        )

    async def _embed_safe(
        text: str, user_id: str, kind: str
    ) -> list[float] | None:
        try:
            from agentic.memory.pg_vector import embed_text
            return await embed_text(text)
        except Exception as exc:
            logger.warning(
                "embed_text failed for %s (user=%s): %s "
                "- node will be synced by retry sweep",
                kind, user_id, exc,
            )
            return None

    async def _safe_link(coro: Any, label: str, user_id: str, session_id: str) -> bool:
        """exec batch"""
        try:
            await coro
            return True
        except Exception as exc:
            logger.warning(
                "Relation link failed [%s] (user=%s session=%s): %s",
                label, user_id, session_id, exc,
            )
            return False

    async def _writer(
        *,
        user_id: str,
        session_id: str,
        summary: str,
        extracted: Sequence[Mapping[str, Any]],
        language: str | None,
    ) -> None:
        from agentic.memory.knowledge_graph.kg_writer import (
            BehaviorInput,
            EmotionInput,
            ExperienceInput,
            MemoryInput,
            SubjectInput,
            PersonInput,     # backward compat alias
            ThoughtInput,
            TriggerInput,
            TopicInput,
            write_behavior,
            write_emotion,
            write_experience,
            write_memory,
            write_subject,
            write_person,    # backward compat alias
            write_thought,
            write_trigger,
            write_topic,
            deactivate_trigger,
            reappraise_experience,
            replace_behavior,
            supersede_thought,
        )
        from agentic.memory.knowledge_graph.kg_retriever.relationships import (
            link_emotion_to_thought,
            link_experience_to_emotion,
            link_experience_to_subject,
            link_experience_to_person,   # backward compat alias
            link_experience_to_trigger,
            link_thought_emotion_association,
            link_to_behavior,
            link_to_topic,
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            await _ensure_kg_anchors(user_id, session_id)
        except Exception as exc:
            logger.error(
                "KG anchor setup failed (user=%s session=%s): %s - "
                "aborting write to prevent ghost pgvector records",
                user_id, session_id, exc,
            )
            return

        memory_importance = _summary_importance(summary, extracted)
        if summary and memory_importance >= 0.5:
            try:
                memory_embedding = await _embed_safe(summary, user_id, "Memory")
                await write_memory(
                    MemoryInput(
                        summary=summary,
                        importance=memory_importance,
                        user_id=user_id,
                        session_id=session_id,
                        embedding=memory_embedding,
                    )
                )
                logger.debug(
                    "Memory node written (user=%s session=%s embedded=%s)",
                    user_id, session_id, memory_embedding is not None,
                )
            except Exception as exc:
                logger.error(
                    "Memory write failed (user=%s session=%s): %s",
                    user_id, session_id, exc,
                )

            # sum onto node.
            try:
                from agentic.memory.neo4j_client import get_client as _gc
                await _gc().execute_write(
                    """
                    MATCH (s:Session {id: $session_id})
                    SET s.summary  = $summary,
                        s.ended_at = coalesce(s.ended_at, datetime())
                    """,
                    {"session_id": session_id, "summary": summary},
                )
            except Exception as exc:
                logger.warning(
                    "Session.summary backfill failed (user=%s session=%s): %s",
                    user_id, session_id, exc,
                )
        elif summary:
            logger.info(
                "Memory summary skipped by quality gate "
                "(user=%s session=%s importance=%.2f)",
                user_id, session_id, memory_importance,
            )

        for fact in extracted:
            thought_ids:  list[str | None] = []
            emotion_ids:  list[str | None] = []
            exp_ids:      list[str | None] = []
            trigger_ids:  list[str | None] = []
            behavior_ids: list[str | None] = []
            subject_ids:  list[str | None] = []
            topic_ids:    list[str | None] = []

            for item in fact.get("thoughts") or []:
                content = (item.get("content") or "").strip()
                if not content or not _should_write_thought(item):
                    thought_ids.append(None)
                    continue
                try:
                    source_message_id = _source_message_id(fact)
                    emb = await _embed_safe(content, user_id, "Thought")
                    thought_input = ThoughtInput(
                        content=content,
                        thought_type=item.get("thought_type") or "automatic",
                        distortion=item.get("distortion") or None,
                        believability=float(item.get("believability") or 0.5),
                        user_id=user_id,
                        session_id=session_id,
                        embedding=emb,
                        source_message_id=source_message_id,
                    )
                    old_thought_id = _clean_optional_str(
                        item.get("supersedes_thought_id")
                    )
                    # supersede if not flagged.
                    if not old_thought_id and emb is not None:
                        try:
                            from agentic.memory.pg_vector import search_thought
                            _sim_hits = await search_thought(
                                user_id, emb, top_k=1, min_similarity=0.92,
                            )
                            if _sim_hits:
                                old_thought_id = _sim_hits[0].neo4j_node_id
                        except Exception as _dedup_exc:
                            logger.debug("Thought dedup probe failed: %s", _dedup_exc)
                    if old_thought_id:
                        tid = await supersede_thought(
                            old_thought_id=old_thought_id,
                            new_thought=thought_input,
                            reason=_supersede_reason(
                                item.get("supersedes_reason")
                            ),
                        )
                    else:
                        tid = await write_thought(thought_input)
                    thought_ids.append(tid)
                except Exception as exc:
                    logger.warning(
                        "Thought write failed (user=%s session=%s): %s",
                        user_id, session_id, exc,
                    )
                    thought_ids.append(None)
            for item in fact.get("emotions") or []:
                label = (item.get("label") or "").strip()
                source_text = (item.get("source_text") or "").strip()
                if not label or not source_text or not _should_write_emotion(item):
                    emotion_ids.append(None)
                    continue
                try:
                    eid = await write_emotion(
                        EmotionInput(
                            label=label,
                            intensity=float(item.get("intensity") or 0.5),
                            valence=float(item.get("valence") or 0.0),
                            source_text=source_text,
                            user_id=user_id,
                            session_id=session_id,
                            source_message_id=_source_message_id(fact),
                        )
                    )
                    emotion_ids.append(eid)
                except Exception as exc:
                    logger.warning(
                        "Emotion write failed (user=%s session=%s): %s",
                        user_id, session_id, exc,
                    )
                    emotion_ids.append(None)
            for item in fact.get("experiences") or []:
                description = (item.get("description") or "").strip()
                if not description or not _should_write_experience(item):
                    exp_ids.append(None)
                    continue
                try:
                    emb = await _embed_safe(description, user_id, "Experience")
                    experience_input = ExperienceInput(
                        description=description,
                        occurred_at=_safe_iso_datetime(item.get("occurred_at"), fallback=now_iso),
                        extracted_at=now_iso,
                        valence=float(item.get("valence") or 0.0),
                        significance=float(item.get("significance") or 0.5),
                        user_id=user_id,
                        session_id=session_id,
                        embedding=emb,
                        source_message_id=_source_message_id(fact),
                    )
                    old_experience_id = _clean_optional_str(
                        item.get("reappraises_experience_id")
                    )
                    if old_experience_id:
                        xid = await reappraise_experience(
                            old_experience_id=old_experience_id,
                            new_experience=experience_input,
                            reason=_lifecycle_reason(
                                item.get("reappraisal_reason"), "user_reappraisal"
                            ),
                        )
                    else:
                        xid = await write_experience(experience_input)
                    exp_ids.append(xid)
                except Exception as exc:
                    logger.warning(
                        "Experience write failed (user=%s session=%s): %s",
                        user_id, session_id, exc,
                    )
                    exp_ids.append(None)
            for item in fact.get("triggers") or []:
                description = (item.get("description") or "").strip()
                if not description or not _should_write_trigger(item):
                    trigger_ids.append(None)
                    continue
                try:
                    emb = await _embed_safe(description, user_id, "Trigger")
                    trid = await write_trigger(
                        TriggerInput(
                            category=item.get("category") or "other",
                            description=description,
                            significance=float(item.get("significance") or 0.5),
                            user_id=user_id,
                            session_id=session_id,
                            embedding=emb,
                            source_message_id=_source_message_id(fact),
                        )
                    )
                    trigger_ids.append(trid)
                except Exception as exc:
                    logger.warning(
                        "Trigger write failed (user=%s session=%s): %s",
                        user_id, session_id, exc,
                    )
                    trigger_ids.append(None)
            for update in fact.get("trigger_updates") or []:
                trigger_id = _clean_optional_str(update.get("trigger_id"))
                action = _clean_optional_str(update.get("action"))
                if not trigger_id or action != "deactivate":
                    continue
                try:
                    await deactivate_trigger(
                        trigger_id=trigger_id,
                        user_id=user_id,
                        session_id=session_id,
                        source_message_id=_source_message_id(fact),
                        reason=_lifecycle_reason(update.get("reason"), "resolved"),
                    )
                except Exception as exc:
                    logger.warning(
                        "Trigger lifecycle failed (user=%s session=%s id=%s): %s",
                        user_id, session_id, trigger_id, exc,
                    )
            for item in fact.get("behaviors") or []:
                description = (item.get("description") or "").strip()
                if not description or not _should_write_behavior(item):
                    behavior_ids.append(None)
                    continue
                try:
                    behavior_embedding = await _embed_safe(description, user_id, "Behavior")
                    behavior_input = BehaviorInput(
                        description=description,
                        category=item.get("category") or "other",
                        adaptive=bool(item.get("adaptive", False)),
                        significance=float(item.get("significance") or 0.5),
                        user_id=user_id,
                        session_id=session_id,
                        embedding=behavior_embedding,
                        source_message_id=_source_message_id(fact),
                    )
                    old_behavior_id = _clean_optional_str(
                        item.get("replaces_behavior_id")
                    )
                    if old_behavior_id:
                        bid = await replace_behavior(
                            old_behavior_id=old_behavior_id,
                            new_behavior=behavior_input,
                            reason=_lifecycle_reason(
                                item.get("replacement_reason"), "replacement"
                            ),
                        )
                    else:
                        bid = await write_behavior(behavior_input)
                    behavior_ids.append(bid)
                except Exception as exc:
                    logger.warning(
                        "Behavior write failed (user=%s session=%s): %s",
                        user_id, session_id, exc,
                    )
                    behavior_ids.append(None)
            for item in (fact.get("subjects") or fact.get("persons")) or []:
                name = (item.get("name") or "").strip()
                role = (item.get("role") or "other").strip()
                if not name:
                    subject_ids.append(None)
                    continue
                try:
                    pid = await write_subject(
                        SubjectInput(
                            name=name,
                            role=role,
                            sentiment=float(item.get("sentiment") or 0.0),
                            subject_type=item.get("subject_type") or "person",
                            relationship_quality=item.get("relationship_quality") or "neutral",
                            user_id=user_id,
                            session_id=session_id,
                            source_message_id=_source_message_id(fact),
                        )
                    )
                    subject_ids.append(pid)
                except Exception as exc:
                    logger.warning(
                        "Subject write failed (user=%s session=%s name=%r): %s",
                        user_id, session_id, name, exc,
                    )
                    subject_ids.append(None)
            for item in fact.get("topics") or []:
                name = (item.get("name") or "").strip()
                if not name or not _should_write_topic(item):
                    topic_ids.append(None)
                    continue
                try:
                    topid = await write_topic(
                        TopicInput(
                            name=name,
                            category=item.get("category") or "other",
                            sentiment=float(item.get("sentiment") or 0.0),
                            user_id=user_id,
                            session_id=session_id,
                            source_message_id=_source_message_id(fact),
                        )
                    )
                    topic_ids.append(topid)
                except Exception as exc:
                    logger.warning(
                        "Topic write failed (user=%s session=%s name=%r): %s",
                        user_id, session_id, name, exc,
                    )
                    topic_ids.append(None)
            relations = fact.get("relations") or {}
            source_message_id = _source_message_id(fact)
            relation_requested = sum(
                len(value) for value in relations.values() if isinstance(value, list)
            ) if isinstance(relations, Mapping) else 0
            relation_written = 0
            relation_skipped = 0
            relation_fallback = 0

            def _coerce_idx(value: Any) -> int | None:
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                return None

            def _pair(pair: Any) -> tuple[int, int] | None:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    return None
                left = _coerce_idx(pair[0])
                right = _coerce_idx(pair[1])
                if left is None or right is None:
                    return None
                return left, right

            def _ids_ok(ids_a: list, idx_a: int, ids_b: list, idx_b: int) -> bool:
                return (
                    0 <= idx_a < len(ids_a) and ids_a[idx_a] is not None
                    and 0 <= idx_b < len(ids_b) and ids_b[idx_b] is not None
                )

            def _valid_indices(ids: list) -> list[int]:
                return [idx for idx, value in enumerate(ids) if value is not None]

            def _fallback_from_single_source(
                src_ids: list,
                dst_ids: list,
            ) -> list[tuple[int, int]]:
                src = _valid_indices(src_ids)
                dst = _valid_indices(dst_ids)
                if len(src) == 1 and dst:
                    return [(src[0], idx) for idx in dst]
                return []

            async def _wire(coro: Any, label: str, fallback: bool = False) -> None:
                nonlocal relation_written, relation_skipped, relation_fallback
                ok = await _safe_link(coro, label, user_id, session_id)
                if ok:
                    relation_written += 1
                    if fallback:
                        relation_fallback += 1
                else:
                    relation_skipped += 1

            def _relation_pairs(key: str, ids_a: list, ids_b: list) -> list[tuple[int, int]]:
                nonlocal relation_skipped
                pairs: list[tuple[int, int]] = []
                for raw_pair in relations.get(key) or []:
                    item = _pair(raw_pair)
                    if item is None:
                        relation_skipped += 1
                        continue
                    idx_a, idx_b = item
                    if _ids_ok(ids_a, idx_a, ids_b, idx_b):
                        pairs.append((idx_a, idx_b))
                    else:
                        relation_skipped += 1
                return pairs

            use_fallback_relations = relation_requested == 0
            exp_trigger_pairs = (
                _fallback_from_single_source(exp_ids, trigger_ids)
                if use_fallback_relations
                else _relation_pairs("experience_to_trigger", exp_ids, trigger_ids)
            )
            for exp_idx, trigger_idx in exp_trigger_pairs:
                await _wire(
                    link_experience_to_trigger(
                        exp_ids[exp_idx], trigger_ids[trigger_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "TRIGGERED_BY",
                    fallback=use_fallback_relations,
                )
            exp_emotion_pairs = (
                _fallback_from_single_source(exp_ids, emotion_ids)
                if use_fallback_relations
                else _relation_pairs("experience_to_emotion", exp_ids, emotion_ids)
            )
            for exp_idx, emotion_idx in exp_emotion_pairs:
                await _wire(
                    link_experience_to_emotion(
                        exp_ids[exp_idx], emotion_ids[emotion_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "TRIGGERED_EMOTION",
                    fallback=use_fallback_relations,
                )
            exp_subject_pairs = (
                _fallback_from_single_source(exp_ids, subject_ids)
                if use_fallback_relations
                else (_relation_pairs("experience_to_subject", exp_ids, subject_ids) or _relation_pairs("experience_to_person", exp_ids, subject_ids))
            )
            for exp_idx, subject_idx in exp_subject_pairs:
                await _wire(
                    link_experience_to_subject(
                        exp_ids[exp_idx], subject_ids[subject_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "INVOLVES_SUBJECT",
                    fallback=use_fallback_relations,
                )
            exp_topic_pairs = (
                _fallback_from_single_source(exp_ids, topic_ids)
                if use_fallback_relations
                else _relation_pairs("experience_to_topic", exp_ids, topic_ids)
            )
            for exp_idx, topic_idx in exp_topic_pairs:
                await _wire(
                    link_to_topic(
                        exp_ids[exp_idx], "Experience", topic_ids[topic_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "RELATED_TO_TOPIC(exp)",
                    fallback=use_fallback_relations,
                )
            emotion_thought_pairs = (
                _fallback_from_single_source(emotion_ids, thought_ids)
                if use_fallback_relations
                else _relation_pairs("emotion_to_thought", emotion_ids, thought_ids)
            )
            for emotion_idx, thought_idx in emotion_thought_pairs:
                await _wire(
                    link_emotion_to_thought(
                        emotion_ids[emotion_idx], thought_ids[thought_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "ACTIVATED_THOUGHT",
                    fallback=use_fallback_relations,
                )
                await _wire(
                    link_thought_emotion_association(
                        thought_ids[thought_idx], emotion_ids[emotion_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "ASSOCIATED_WITH",
                    fallback=use_fallback_relations,
                )
            emotion_behavior_pairs = (
                _fallback_from_single_source(emotion_ids, behavior_ids)
                if use_fallback_relations and not _valid_indices(thought_ids)
                else _relation_pairs("emotion_to_behavior", emotion_ids, behavior_ids)
            )
            for emotion_idx, behavior_idx in emotion_behavior_pairs:
                await _wire(
                    link_to_behavior(
                        emotion_ids[emotion_idx], "Emotion", behavior_ids[behavior_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "LED_TO_BEHAVIOR(emo)",
                    fallback=use_fallback_relations,
                )
            thought_behavior_pairs = (
                _fallback_from_single_source(thought_ids, behavior_ids)
                if use_fallback_relations
                else _relation_pairs("thought_to_behavior", thought_ids, behavior_ids)
            )
            for thought_idx, behavior_idx in thought_behavior_pairs:
                await _wire(
                    link_to_behavior(
                        thought_ids[thought_idx], "Thought", behavior_ids[behavior_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "LED_TO_BEHAVIOR(thought)",
                    fallback=use_fallback_relations,
                )
            emotion_topic_pairs = (
                _fallback_from_single_source(emotion_ids, topic_ids)
                if use_fallback_relations
                else _relation_pairs("emotion_to_topic", emotion_ids, topic_ids)
            )
            for emotion_idx, topic_idx in emotion_topic_pairs:
                await _wire(
                    link_to_topic(
                        emotion_ids[emotion_idx], "Emotion", topic_ids[topic_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "RELATED_TO_TOPIC(emo)",
                    fallback=use_fallback_relations,
                )
            thought_topic_pairs = (
                _fallback_from_single_source(thought_ids, topic_ids)
                if use_fallback_relations
                else _relation_pairs("thought_to_topic", thought_ids, topic_ids)
            )
            for thought_idx, topic_idx in thought_topic_pairs:
                await _wire(
                    link_to_topic(
                        thought_ids[thought_idx], "Thought", topic_ids[topic_idx], session_id,
                        source_message_id=source_message_id,
                    ),
                    "RELATED_TO_TOPIC(thought)",
                    fallback=use_fallback_relations,
                )

            logger.info(
                "kg_writer counts user=%s session=%s thoughts=%d emotions=%d "
                "experiences=%d triggers=%d behaviors=%d subjects=%d topics=%d "
                "relations_requested=%d relations_written=%d relations_skipped=%d "
                "relations_fallback=%d",
                user_id, session_id,
                sum(1 for x in thought_ids  if x),
                sum(1 for x in emotion_ids  if x),
                sum(1 for x in exp_ids      if x),
                sum(1 for x in trigger_ids  if x),
                sum(1 for x in behavior_ids if x),
                sum(1 for x in subject_ids  if x),
                sum(1 for x in topic_ids    if x),
                relation_requested,
                relation_written,
                relation_skipped,
                relation_fallback,
            )

    return _writer  # type: ignore[return-value]


def build_session_finalizer() -> SessionFinalizer:
    """finalize"""
    return SessionFinalizer(
        history_loader=make_history_loader(),
        summarizer=make_summarizer(),
        extractor=make_kg_extractor(),
        kg_writer=make_kg_writer(),
        session_metadata_loader=make_session_metadata_loader(),
        user_context_loader=make_user_context_loader(),
    )


__all__ = [
    "build_session_finalizer",
    "make_history_loader",
    "make_session_metadata_loader",
    "make_user_context_loader",
    "make_summarizer",
    "make_kg_extractor",
    "make_kg_writer",
]

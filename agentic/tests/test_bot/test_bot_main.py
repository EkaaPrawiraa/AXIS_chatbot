"""buat bot cli"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Iterable

from agentic.agent.tools.context_awareness_tool import (
    calculate_math,
    current_context,
    resolve_relative_time,
    web_search,
)

# `langchain providers`
try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover -- langchain-openai not installed
    ChatOpenAI = None  # type: ignore[assignment]

try:
    from langchain_anthropic import ChatAnthropic
except Exception:  # pragma: no cover -- langchain-anthropic not installed
    ChatAnthropic = None  # type: ignore[assignment]

try:
    from groq import Groq
except Exception:  # pragma: no cover -- groq not installed
    Groq = None  # type: ignore[assignment]

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage

from agentic.agent.nodes.dialogue_policy import dialogue_policy_node
from agentic.agent.nodes.memory_retrieval import memory_retrieval_node
from agentic.agent.nodes.response_generator import response_generator_node
from agentic.agent.nodes.session_end import session_end_node
from agentic.agent.state import (
    ConversationState,
    empty_phq9_state,
    empty_voice_state,
)
from agentic.agent.audit.guardrail_events import GuardrailEvent, GuardrailLogger

# import per mod.
from agentic.memory import neo4j_client as nc
from agentic.memory.context_builder import build_context

from agentic.memory.knowledge_graph.kg_retriever import (
    # inisialisasi data
    BehaviorInput,
    EmotionInput,
    ExperienceInput,
    MemoryInput,
    PersonInput,
    ThoughtInput,
    TriggerInput,
    # buat ngbuild relas.
    link_emotion_to_thought,
    link_experience_to_emotion,
    link_experience_to_person,
    link_experience_to_trigger,
    link_thought_emotion_association,
    link_to_behavior,
    # look up provenance
    facts_for_message,
    nodes_for_message,
    # per-label point-reads
    read_behavior,
    read_emotion,
    read_experience,
    read_memory,
    read_person,
    read_thought,
    read_trigger,
)
from agentic.memory.knowledge_graph.kg_writer import (
    write_behavior,
    write_emotion,
    write_experience,
    write_memory,
    write_person,
    write_thought,
    write_trigger,
)
from agentic.memory.knowledge_graph.kg_modifier import update_node_property
from agentic.memory.knowledge_graph.kg_algorithm import run_memory_decay, supersede_thought

# arch / purge pgvector in one call
from agentic.memory.cross_store_sync import (
    invalidate_message_full,
    purge_message_full,
    purge_user_full,
    sweep_unsynced,
)

# pgvec adapter - only embedder needed. Cosine search & dedup transparent.
from agentic.memory.pg_vector import embed_text


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_bot")


class StdoutGuardrailLogger:
    """log debug/trace"""

    def __init__(
        self,
        *,
        enabled: bool = False,
        include_metadata: bool = False,
        only_cbt_and_memory: bool = True,
    ) -> None:
        self.enabled = enabled
        self.include_metadata = include_metadata
        self.only_cbt_and_memory = only_cbt_and_memory
        self.events: list[GuardrailEvent] = []

    def _should_print(self, event: GuardrailEvent) -> bool:
        if not self.only_cbt_and_memory:
            return True
        if event.event_type in ("memory_retrieved", "response_generated", "tool_called"):
            return True
        if event.event_type.startswith("cbt_"):
            return True
        return False

    async def log(self, event: GuardrailEvent) -> None:
        self.events.append(event)
        if not self.enabled:
            return
        if not self._should_print(event):
            return

        print(f"[audit] {event.to_log_line()}")
        if self.include_metadata and event.metadata:
            try:
                raw = json.dumps(dict(event.metadata), ensure_ascii=False, default=str)
            except Exception:
                raw = str(event.metadata)
            if len(raw) > 800:
                raw = raw[:797] + "..."
            print(f"[audit.meta] {raw}")


def _init_node_state(*, user_id: str, session_id: str) -> ConversationState:
    """init state"""
    return {
        "user_id": user_id,
        "session_id": session_id,
        "messages": [],
        "current_message": "",
        "session_turn": 0,
        "resolved_language": os.getenv("DEFAULT_USER_LANGUAGE", "id"),
        "kg_context": None,
        "response_draft": None,
        "final_response": None,
        "safety_flag": None,
        "cbt_state": None,
        "cbt_node_active": None,
        "cbt_directive": None,
        "phq9_state": empty_phq9_state(),
        "voice_state": empty_voice_state(),
    }


def _reset_turn_transients(state: ConversationState) -> None:
    """cleanup"""
    state["response_draft"] = None
    state["final_response"] = None
    state["kg_context"] = None
    state["safety_flag"] = None
    state.pop("input_guardrail", None)
    state.pop("crisis_escalated", None)


# aware

BOT_TOOLS = [
    current_context,
    resolve_relative_time,
    calculate_math,
    web_search,
]
_TOOLS_BY_NAME = {t.name: t for t in BOT_TOOLS}


def _bind_tools_if_supported(llm: Any) -> Any:
    """bind tools"""
    binder = getattr(llm, "bind_tools", None)
    if callable(binder):
        try:
            return binder(BOT_TOOLS)
        except Exception as exc:
            logger.warning("bind_tools failed (%s); continuing without tool-calling", exc)
    return llm


def _get_tool_calls(msg: Any) -> list[dict[str, Any]]:
    """skip klo error"""
    calls = getattr(msg, "tool_calls", None)
    if isinstance(calls, list):
        return [c for c in calls if isinstance(c, dict)]

    kw = getattr(msg, "additional_kwargs", None)
    if isinstance(kw, dict) and isinstance(kw.get("tool_calls"), list):
        return [c for c in kw["tool_calls"] if isinstance(c, dict)]

    return []


async def _ainvoke_with_tools(llm: Any, messages: list[Any], *, max_hops: int = 6) -> AIMessage:
    """run llm with tools"""
    working: list[Any] = list(messages)
    web_urls: list[str] = []
    web_seen: set[str] = set()
    last: Any = None
    for _ in range(max_hops):
        last = await llm.ainvoke(working)
        tool_calls = _get_tool_calls(last)
        if not tool_calls:
            break

        working.append(last)
        for call in tool_calls:
            name = call.get("name")
            args = call.get("args")
            call_id = call.get("id")
            tool = _TOOLS_BY_NAME.get(name)

            if tool is None:
                result: dict[str, Any] = {"error": f"unknown tool: {name}"}
            else:
                try:
                    payload = args if isinstance(args, dict) else {}
                    result = tool.invoke(payload)
                except Exception as exc:
                    result = {"error": f"tool failed: {exc}"}

            # capture ref urls
            if name == "web_search" and isinstance(result, dict):
                rows = result.get("results")
                if isinstance(rows, list):
                    for row in rows:
                        if not isinstance(row, dict):
                            continue
                        url = row.get("url")
                        if isinstance(url, str):
                            url = url.strip()
                        if url and url not in web_seen:
                            web_seen.add(url)
                            web_urls.append(url)

            content = json.dumps(result, ensure_ascii=False, default=str)
            if call_id:
                working.append(ToolMessage(content=content, tool_call_id=call_id))
            else:
                working.append(ToolMessage(content=content, tool_call_id="tool_call"))

    if isinstance(last, AIMessage):
        last.additional_kwargs = dict(getattr(last, "additional_kwargs", {}) or {})
        last.additional_kwargs["web_search_urls"] = web_urls
        return last
    # wrap unkown return.
    msg = AIMessage(content=str(getattr(last, "content", last)))
    msg.additional_kwargs = dict(getattr(msg, "additional_kwargs", {}) or {})
    msg.additional_kwargs["web_search_urls"] = web_urls
    return msg



SYSTEM_PROMPT = """You are a warm, evidence-based mental health companion.
You are running inside a TEST HARNESS that exercises the long-term memory
graph. After your normal reply, you MUST append a fenced JSON block tagged
``kg`` describing what the conversation revealed for the knowledge graph.

You may use tools when needed to answer accurately:
- current_context (current date/time/timezone)
- resolve_relative_time (e.g. "tomorrow 5pm")
- calculate_math (safe arithmetic)
- web_search (OpenAI)

Reply format:

<reply>your conversational reply here</reply>

```kg
{
  "experience":   { "description": "...", "valence": -0.4, "significance": 0.5 } | null,
  "emotion":      { "label": "...", "intensity": 0.0, "valence": 0.0,
                    "arousal": 0.0, "dominance": 0.0,
                    "source_text": "..." } | null,
  "thought":      { "content": "...", "thought_type": "automatic|core_belief|intermediate",
                    "distortion": "catastrophizing|...|null",
                    "believability": 0.0 } | null,
  "trigger":      { "category": "academic|social|family|work|...",
                    "description": "...",
                    "aliases": [] } | null,
  "behavior":     { "description": "...", "category": "avoidance|...",
                    "adaptive": true|false } | null,
  "subject":      { "name": "...", "role": "...",
                    "subject_type": "person|pet|object|place|other",
                    "sentiment": -1.0..1.0,
                    "relationship_quality": "supportive|complicated|negative|neutral" } | null
}
```

Rules:
* Omit fields with null when nothing was revealed; never invent.
* Use the user's wording in description/content fields.
* Keep distortions to the canonical 10: catastrophizing, mind_reading,
  all_or_nothing, fortune_telling, emotional_reasoning, should_statements,
  labeling, magnification, personalization, overgeneralization.
* Numbers must be floats in their declared ranges.

Long-term memory context for this user (use it; do not repeat verbatim):
{{KG_CONTEXT}}
"""

# skip klo error
_KG_CONTEXT_SENTINEL = "{{KG_CONTEXT}}"


def render_system_prompt(kg_context: str) -> str:
    """inject live kg into static prompt"""
    return SYSTEM_PROMPT.replace(_KG_CONTEXT_SENTINEL, kg_context)



class _GroqChatAdapter:
    """adapt for LangChain"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_completion_tokens: int | None,
    ) -> None:
        if Groq is None:  # pragma: no cover
            raise RuntimeError("Groq SDK not installed. `pip install groq`.")
        self._client = Groq(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_completion_tokens = max_completion_tokens

    @staticmethod
    def _to_groq_messages(messages: list[Any]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for m in messages:
            if isinstance(m, SystemMessage):
                role = "system"
            elif isinstance(m, HumanMessage):
                role = "user"
            elif isinstance(m, AIMessage):
                role = "assistant"
            else:
                # fallback for any other msg type
                role = getattr(m, "type", None) or "user"

            content = getattr(m, "content", "")
            out.append({"role": role, "content": str(content)})
        return out

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        payload: dict[str, Any] = {
            "model":       self._model,
            "messages":    self._to_groq_messages(messages),
            "temperature": self._temperature,
        }
        if self._max_completion_tokens is not None:
            payload["max_completion_tokens"] = self._max_completion_tokens

        # skip klo async
        def _call():
            return self._client.chat.completions.create(**payload)

        resp = await asyncio.to_thread(_call)
        content = (resp.choices[0].message.content or "") if resp.choices else ""
        return AIMessage(content=content)


def _make_groq_llm() -> _GroqChatAdapter:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    model = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    temperature = float(os.getenv("GROQ_TEMPERATURE", "0.4"))
    max_tokens_raw = os.getenv("GROQ_MAX_COMPLETION_TOKENS")
    max_tokens = int(max_tokens_raw) if max_tokens_raw else None
    return _GroqChatAdapter(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )


def _make_llm():
    """`ng ambil client`"""
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    print(provider)

    def _make_openai():
        print(os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        print(float(os.getenv("OPENAI_TEMPERATURE", "1")))
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "1")),
        )

    def _make_anthropic():
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.4")),
        )

    if provider == "openai":
        if not (os.getenv("OPENAI_API_KEY") and ChatOpenAI is not None):
            raise RuntimeError("LLM_PROVIDER=openai but OpenAI is not available")
        return _make_openai()
    if provider == "anthropic":
        if not (os.getenv("ANTHROPIC_API_KEY") and ChatAnthropic is not None):
            raise RuntimeError("LLM_PROVIDER=anthropic but Anthropic is not available")
        return _make_anthropic()
    if provider == "groq":
        return _make_groq_llm()

    # default pri: OpenAI, then Anthropic, then Groq.
    if os.getenv("OPENAI_API_KEY") and ChatOpenAI is not None:
        return _make_openai()
    if os.getenv("ANTHROPIC_API_KEY") and ChatAnthropic is not None:
        return _make_anthropic()
    if os.getenv("GROQ_API_KEY"):
        return _make_groq_llm()

    raise RuntimeError(
        "No LLM available. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY "
        "and install the matching client package(s)."
    )



_REPLY_RE = re.compile(r"<reply>(?P<body>.*?)</reply>", re.DOTALL | re.IGNORECASE)
_KG_RE    = re.compile(r"```kg\s*(?P<json>{.*?})\s*```", re.DOTALL | re.IGNORECASE)


@dataclass
class TurnOutput:
    reply: str
    kg:    dict[str, Any]


def parse_turn(raw: str) -> TurnOutput:
    """pull reply, block, optional, parse fail, return raw text."""
    reply_match = _REPLY_RE.search(raw)
    kg_match    = _KG_RE.search(raw)

    reply = reply_match.group("body").strip() if reply_match else raw.strip()
    kg: dict[str, Any] = {}
    if kg_match:
        try:
            kg = json.loads(kg_match.group("json"))
        except json.JSONDecodeError as exc:
            logger.warning("KG block was not valid JSON: %s", exc)
    return TurnOutput(reply=reply, kg=kg)


# track msg_id, skip errors

@dataclass
class TurnRecord:
    """ngambil ids"""
    index:      int
    message_id: str
    user_text:  str
    reply:      str
    node_ids:   dict[str, str | None] = field(default_factory=dict)


class TurnLog:
    """mbungkus data, akses `/`"""

    def __init__(self, capacity: int = 50) -> None:
        self._records: list[TurnRecord] = []
        self._capacity = capacity

    def add(self, record: TurnRecord) -> None:
        self._records.append(record)
        if len(self._records) > self._capacity:
            self._records.pop(0)

    def latest(self, n: int = 10) -> list[TurnRecord]:
        return self._records[-n:]

    def by_index(self, idx: int) -> TurnRecord | None:
        for rec in self._records:
            if rec.index == idx:
                return rec
        return None

    def resolve(self, ref: str) -> str | None:
        """resolve msg_id"""
        ref = ref.strip()
        if not ref:
            return None
        if ref.startswith("#"):
            try:
                idx = int(ref[1:])
            except ValueError:
                return None
            rec = self.by_index(idx)
            return rec.message_id if rec else None
        return ref



# Labels, update_node, validate_input.
_READABLE_LABELS: dict[str, Callable[[str], Awaitable[Any]]] = {
    "Behavior":   read_behavior,
    "Emotion":    read_emotion,
    "Experience": read_experience,
    "Memory":     read_memory,
    "Subject":    read_person,
    "Thought":    read_thought,
    "Trigger":    read_trigger,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _safe_embed(text: str | None) -> list[float] | None:
    """None on fail. Sync'd by retry sweep."""
    if not text or not text.strip():
        return None
    try:
        return await embed_text(text)
    except Exception as exc:
        logger.warning("embed_text failed (%s): leaving node unsynced", exc)
        return None


# log every byte to Neo4j/pgvector

trace = logging.getLogger("test_bot.trace")

_TRACE_MAX_FIELD_LEN = 160   # clip long strings in payload dumps
_TRACE_MAX_LIST_LEN  = 6     # show first N items of any list field


def _trim_for_trace(value: Any) -> Any:
    """safe_val"""
    if isinstance(value, str):
        return value if len(value) <= _TRACE_MAX_FIELD_LEN else value[:_TRACE_MAX_FIELD_LEN] + "..."
    if isinstance(value, list):
        head = [_trim_for_trace(v) for v in value[:_TRACE_MAX_LIST_LEN]]
        return head + (["..."] if len(value) > _TRACE_MAX_LIST_LEN else [])
    if isinstance(value, dict):
        return {k: _trim_for_trace(v) for k, v in value.items()}
    return value


def _embedding_marker(embedding: list[float] | None) -> str:
    """write to db"""
    if embedding is None:
        return "Neo4j only"
    return f"Neo4j + pgvector (dim={len(embedding)})"


def _log_kg_write(
    label:     str,
    payload:   dict[str, Any],
    *,
    embedding: list[float] | None = None,
) -> None:
    """log line per writer, payload trimmed."""
    trace.info(
        "[KG WRITE] %-10s | %s | payload=%s",
        label,
        _embedding_marker(embedding),
        json.dumps(_trim_for_trace(payload), ensure_ascii=False, default=str),
    )


def _log_kg_write_result(label: str, node_id: str | None) -> None:
    if node_id:
        trace.info("[KG WRITE] %-10s ok | id=%s", label, node_id)
    else:
        trace.warning("[KG WRITE] %-10s skipped (no id returned)", label)


def _log_kg_edge(
    src_label: str, src_id: str,
    edge:      str,
    dst_label: str, dst_id: str,
) -> None:
    trace.info(
        "[KG EDGE]  (%s %s) -[%s]-> (%s %s)",
        src_label, src_id, edge, dst_label, dst_id,
    )


def _log_pg_read(line: str, embedding: list[float] | None) -> None:
    if embedding is None:
        trace.info("[PG READ]  query embedding skipped (signal 2 disabled)")
        return
    trace.info(
        "[PG READ]  query embedding | dim=%d | line=%r",
        len(embedding),
        _trim_for_trace(line),
    )


def _log_kg_read_summary(retrieved: Any) -> None:
    """get data"""
    trace.info(
        "[KG READ]  context | recency=%d semantic=%d salient=%d "
        "experiences=%d people=%d emotions=%d distortions=%d triggers=%d",
        len(retrieved.recency_summaries),
        len(retrieved.semantic_memories),
        len(retrieved.salient_memories),
        len(getattr(retrieved, "semantic_experiences", []) or []),
        len(getattr(retrieved, "important_people", []) or []),
        len(retrieved.active_emotions),
        len(retrieved.active_distortions),
        len(retrieved.recurring_triggers),
    )


async def apply_kg_block(
    block:      dict[str, Any],
    *,
    user_id:    str,
    session_id: str,
    message_id: str,
) -> dict[str, str | None]:
    """get node ids"""
    ids: dict[str, str | None] = {
        "experience": None, "emotion": None, "thought": None,
        "trigger":    None, "behavior": None, "subject": None,
    }

    if exp := block.get("experience"):
        now            = _now_iso()
        description    = exp["description"]
        exp_embedding  = await _safe_embed(description)
        exp_payload = {
            "description":       description,
            "occurred_at":       exp.get("occurred_at", now),
            "extracted_at":      now,
            "valence":           float(exp.get("valence", 0.0)),
            "significance":      float(exp.get("significance", 0.5)),
            "user_id":           user_id,
            "session_id":        session_id,
            "source_message_id": message_id,
        }
        _log_kg_write("Experience", exp_payload, embedding=exp_embedding)
        ids["experience"] = await write_experience(ExperienceInput(
            **exp_payload,
            embedding=exp_embedding,
        ))
        _log_kg_write_result("Experience", ids["experience"])

    if emo := block.get("emotion"):
        emo_payload = {
            "label":             emo["label"],
            "intensity":         float(emo.get("intensity", 0.5)),
            "valence":           float(emo.get("valence", 0.0)),
            "arousal":           float(emo.get("arousal", 0.0)),
            "dominance":         float(emo.get("dominance", 0.0)),
            "source_text":       emo.get("source_text", ""),
            "user_id":           user_id,
            "session_id":        session_id,
            "source_message_id": message_id,
        }
        _log_kg_write("Emotion", emo_payload, embedding=None)
        # pyrefly: ignore [unexpected-keyword]
        ids["emotion"] = await write_emotion(EmotionInput(**emo_payload))
        _log_kg_write_result("Emotion", ids["emotion"])

    if th := block.get("thought"):
        content       = th["content"]
        th_embedding  = await _safe_embed(content)
        th_payload = {
            "content":           content,
            "thought_type":      th.get("thought_type", "automatic"),
            "distortion":        th.get("distortion"),
            "believability":     float(th.get("believability", 0.5)),
            "user_id":           user_id,
            "session_id":        session_id,
            "source_message_id": message_id,
        }
        _log_kg_write("Thought", th_payload, embedding=th_embedding)
        ids["thought"] = await write_thought(ThoughtInput(
            **th_payload,
            embedding=th_embedding,
        ))
        _log_kg_write_result("Thought", ids["thought"])

    if trig := block.get("trigger"):
        trig_description = trig["description"]
        trig_embedding   = await _safe_embed(trig_description)
        trig_payload = {
            "category":          trig["category"],
            "description":       trig_description,
            "significance":      float(trig.get("significance", 0.7)),
            "user_id":           user_id,
            "session_id":        session_id,
            "aliases":           trig.get("aliases") or [],
            "source_message_id": message_id,
        }
        _log_kg_write("Trigger", trig_payload, embedding=trig_embedding)
        ids["trigger"] = await write_trigger(TriggerInput(
            **trig_payload,
            embedding=trig_embedding,
        ))
        _log_kg_write_result("Trigger", ids["trigger"])

    if beh := block.get("behavior"):
        beh_payload = {
            "description":       beh["description"],
            "category":          beh.get("category", "avoidance"),
            "adaptive":          bool(beh.get("adaptive", False)),
            "significance":      float(beh.get("significance", 0.7)),
            "user_id":           user_id,
            "session_id":        session_id,
            "source_message_id": message_id,
        }
        _log_kg_write("Behavior", beh_payload, embedding=None)
        ids["behavior"] = await write_behavior(BehaviorInput(**beh_payload))
        _log_kg_write_result("Behavior", ids["behavior"])

    if per := (block.get("subject") or block.get("person")):
        per_payload = {
            "name":                 per["name"],
            "role":                 per.get("role", "unknown"),
            "subject_type":         per.get("subject_type", "person"),
            "sentiment":            float(per.get("sentiment", 0.0)),
            "user_id":              user_id,
            "session_id":           session_id,
            "relationship_quality": per.get("relationship_quality", "neutral"),
            "source_message_id":    message_id,
        }
        _log_kg_write("Subject", per_payload, embedding=None)
        ids["subject"] = await write_person(PersonInput(**per_payload))
        _log_kg_write_result("Subject", ids["subject"])

    # wire up edges, use source_msg_id, trace edges, see full graph.
    if ids["experience"] and ids["trigger"]:
        _log_kg_edge("Experience", ids["experience"], "TRIGGERED_BY",
                     "Trigger", ids["trigger"])
        await link_experience_to_trigger(
            ids["experience"], ids["trigger"], session_id,
            source_message_id=message_id,
        )
    if ids["experience"] and ids["emotion"]:
        _log_kg_edge("Experience", ids["experience"], "EVOKED",
                     "Emotion", ids["emotion"])
        await link_experience_to_emotion(
            ids["experience"], ids["emotion"], session_id,
            source_message_id=message_id,
        )
    if ids["emotion"] and ids["thought"]:
        _log_kg_edge("Emotion", ids["emotion"], "DROVE",
                     "Thought", ids["thought"])
        await link_emotion_to_thought(
            ids["emotion"], ids["thought"], session_id,
            source_message_id=message_id,
        )
        _log_kg_edge("Thought", ids["thought"], "ASSOCIATED_WITH",
                     "Emotion", ids["emotion"])
        await link_thought_emotion_association(
            ids["thought"], ids["emotion"], session_id, strength=0.8,
            source_message_id=message_id,
        )
    if ids["emotion"] and ids["behavior"]:
        _log_kg_edge("Emotion", ids["emotion"], "LED_TO",
                     "Behavior", ids["behavior"])
        await link_to_behavior(
            ids["emotion"], "Emotion", ids["behavior"], session_id,
            source_message_id=message_id,
        )
    if ids["thought"] and ids["behavior"]:
        _log_kg_edge("Thought", ids["thought"], "LED_TO",
                     "Behavior", ids["behavior"])
        await link_to_behavior(
            ids["thought"], "Thought", ids["behavior"], session_id,
            source_message_id=message_id,
        )
    if ids["experience"] and ids["subject"]:
        _log_kg_edge("Experience", ids["experience"], "INVOLVES_SUBJECT",
                     "Subject", ids["subject"])
        await link_experience_to_person(
            ids["experience"], ids["subject"], session_id,
            source_message_id=message_id,
        )

    return ids



HELP_TEXT = """
Slash commands:
  /help                              this message
  /context                           context block built for the next turn
    /ctx                               print current datetime/timezone context
    /calc <expression>                 calculate basic math (safe)
    /time [--tz <Zone>] <text>         resolve relative time (e.g. "tomorrow 5pm")
        /search [--n <k>] <query>          web search via OpenAI
  /flush                             run the idle-flush worker once
  /decay                             run the memory decay job once
  /sweep                             reconcile pgvector rows out of sync
  /snapshot                          one-screen view of the user's KG
  /history [n]                       list the last n turns and their ids
  /facts <#turn|message_id>          facts_for_message(...)
  /node <Label> <node_id>            kg_retriever.read_<label>(node_id)
  /update <Label> <node_id> <prop> <value>
                                     kg_modifier.update_node_property(...)
  /soft <#turn|message_id> [reason]  cross_store_sync.invalidate_message_full(...)
  /purge <#turn|message_id>          cross_store_sync.purge_message_full(...)
  /wipe-user <user_id>               cross_store_sync.purge_user_full(...)
  /supersede <thought_id> <content>  kg_algorithm.supersede_thought(...)
  /end [summary]                     write a Memory summary and exit
""".strip()


def _append_references(reply: str, urls: list[str]) -> str:
    if not urls:
        return reply
    out = reply.rstrip()
    out += "\n\nReferensi:\n"
    for url in urls:
        out += f"- {url}\n"
    return out.rstrip()

async def _run_cbt_dialogue_policy(state: dict[str, Any]) -> dict[str, Any]:
    """skip klo error"""
    try:
        module = importlib.import_module("agentic.agent.nodes.dialogue_policy")
    except Exception:
        return state

    node_fn = getattr(module, "dialogue_policy_node", None) or getattr(module, "cbt_node", None)
    if node_fn is None:
        return state

    try:
        out = node_fn(state)
        if asyncio.iscoroutine(out):
            out = await out
        return out if isinstance(out, dict) else state
    except Exception as exc:
        logger.warning("CBT/dialogue policy hook failed (%s); continuing", exc)
        return state


def _format_search(result: dict[str, Any]) -> str:
    if not result:
        return "  (no result)"
    if err := result.get("error"):
        return f"  error: {err}"
    rows = result.get("results")
    if not rows:
        return "  (no results)"
    out: list[str] = []
    for i, item in enumerate(rows, 1):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip() or "(untitled)"
        url = (item.get("url") or "").strip()
        if url:
            out.append(f"  {i}. {title}\n      {url}")
        else:
            out.append(f"  {i}. {title}")
    return "\n".join(out)


# `helpers`

def _parse_value(raw: str) -> Any:
    """update values: json, then str."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _format_node_props(props: dict[str, Any] | None) -> str:
    if not props:
        return "<not found>"
    keys = sorted(props.keys())
    width = max(len(k) for k in keys)
    return "\n".join(f"  {k:<{width}}  {props[k]!r}" for k in keys)


def _format_facts(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    if not rows:
        return "  (no active facts attribute this message)"
    out: list[str] = []
    for r in rows:
        src = ":".join(r["src_labels"])
        dst = ":".join(r["dst_labels"])
        out.append(
            f"  ({src} {r['src_id']}) -[{r['edge_type']} "
            f"conf={r['confidence']:.2f}]-> "
            f"({dst} {r['dst_id']})"
        )
    return "\n".join(out)


# snap.

async def cmd_snapshot(user_id: str) -> str:
    client = nc.get_client()
    rows = await client.execute_read(
        """
        MATCH (u:User {id: $uid})
        OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
        WITH u, count(DISTINCT s) AS sessions
        OPTIONAL MATCH (u)-[:EXPERIENCED]->(e:Experience)
        WITH u, sessions, count(DISTINCT e) AS experiences
        OPTIONAL MATCH (u)-[:FELT]->(em:Emotion)
        WITH u, sessions, experiences, count(DISTINCT em) AS emotions
        OPTIONAL MATCH (u)-[:HAS_THOUGHT]->(th:Thought)
        WITH u, sessions, experiences, emotions,
             count(DISTINCT th)                                 AS thoughts,
             count(DISTINCT CASE WHEN th.active THEN th END)    AS active_thoughts
        OPTIONAL MATCH (u)-[:HAS_TRIGGER]->(t:Trigger)
        WITH u, sessions, experiences, emotions, thoughts, active_thoughts,
             count(DISTINCT t) AS triggers
        OPTIONAL MATCH (u)-[:HAS_MEMORY]->(m:Memory)
        WITH u, sessions, experiences, emotions, thoughts, active_thoughts,
             triggers, count(DISTINCT m) AS memories
        OPTIONAL MATCH (u)-[:HAS_SUBJECT]->(p:Subject)
        RETURN sessions, experiences, emotions, thoughts, active_thoughts,
               triggers, memories,
               count(DISTINCT p) AS people
        """,
        {"uid": user_id},
    )
    if not rows:
        return "No data for user yet."
    r = rows[0]
    return (
        f"Sessions: {r['sessions']}  Experiences: {r['experiences']}  "
        f"Emotions: {r['emotions']}\n"
        f"Thoughts: {r['thoughts']} (active {r['active_thoughts']})  "
        f"Triggers: {r['triggers']}  "
        f"Memories: {r['memories']}  People: {r['people']}"
    )


# buat ngequery

def cmd_history(log: TurnLog, n: int = 10) -> str:
    records = log.latest(n)
    if not records:
        return "  (no turns yet)"
    out: list[str] = []
    for rec in records:
        written = {k: v for k, v in rec.node_ids.items() if v}
        snippet = (rec.user_text[:60] + "...") if len(rec.user_text) > 60 else rec.user_text
        out.append(f"  #{rec.index:>3}  {rec.message_id}  {snippet}")
        if written:
            out.append(f"        ids: {written}")
    return "\n".join(out)


# facts.

async def cmd_facts(log: TurnLog, ref: str) -> str:
    message_id = log.resolve(ref)
    if not message_id:
        return f"  cannot resolve '{ref}' to a message id (try /history)"
    rows = await facts_for_message(message_id)
    nodes = await nodes_for_message(message_id)
    head  = f"  message_id={message_id}  (touched {len(nodes)} node(s))"
    return head + "\n" + _format_facts(rows)


# skip

async def cmd_node(label: str, node_id: str) -> str:
    reader = _READABLE_LABELS.get(label)
    if reader is None:
        return f"  unknown label '{label}'. Pick one of: {', '.join(sorted(_READABLE_LABELS))}"
    props = await reader(node_id)
    return f"  {label} {node_id}\n{_format_node_props(props)}"


# update.

async def cmd_update(label: str, node_id: str, prop: str, value_raw: str) -> str:
    if label not in _READABLE_LABELS:
        return f"  unknown label '{label}'. Pick one of: {', '.join(sorted(_READABLE_LABELS))}"
    value = _parse_value(value_raw)
    affected = await update_node_property(label, node_id, {prop: value})
    return f"  update_node_property({label}, {node_id}, {{{prop!r}: {value!r}}}) -> {affected} updated"


# purge, sync, delete.

async def cmd_soft(log: TurnLog, ref: str, reason: str) -> str:
    message_id = log.resolve(ref)
    if not message_id:
        return f"  cannot resolve '{ref}' to a message id"
    counters = await invalidate_message_full(message_id, reason=reason)
    return (
        f"  invalidate_message_full({message_id}, reason={reason!r}) -> "
        f"{json.dumps(counters)}"
    )


async def cmd_purge(log: TurnLog, ref: str) -> str:
    message_id = log.resolve(ref)
    if not message_id:
        return f"  cannot resolve '{ref}' to a message id"
    counters = await purge_message_full(message_id)
    return f"  purge_message_full({message_id}) -> {json.dumps(counters)}"


async def cmd_sweep() -> str:
    """reconcile stuck nodes."""
    counters = await sweep_unsynced()
    return f"  sweep_unsynced() -> {json.dumps(counters)}"


async def cmd_wipe_user(target_user_id: str) -> str:
    """delete traces"""
    counters = await purge_user_full(target_user_id)
    return f"  purge_user_full({target_user_id}) -> {json.dumps(counters)}"


# supersede

async def cmd_supersede(
    *,
    user_id:        str,
    session_id:     str,
    old_thought_id: str,
    new_content:    str,
) -> str:
    new_id = await supersede_thought(
        old_thought_id,
        ThoughtInput(
            content=new_content,
            thought_type="intermediate",
            distortion=None,
            believability=0.5,
            user_id=user_id,
            session_id=session_id,
        ),
        reason="user_reframe",
    )
    return f"  supersede_thought({old_thought_id}) -> new Thought {new_id}"


# buat summary

_SUMMARY_SYSTEM_PROMPT = (
    "You write factual session summaries for a long-term memory store. "
    "Produce 2 to 4 sentences in plain prose. Mention every subject (person, "
    "pet, object, or place) the user named, what each of them did, and the "
    "user's dominant emotional state. Use the user's wording where possible. "
    "No headers, no bullets, no quotation marks around the whole summary."
)


async def _summarize_history(llm: Any, history: list[Any]) -> str:
    """compress into one par", "mention subjects/exps/emotions", "fallback on error"""
    if not history:
        return "Session had no user messages."

    transcript_lines: list[str] = []
    for m in history:
        if isinstance(m, HumanMessage):
            role = "User"
        elif isinstance(m, AIMessage):
            role = "Assistant"
        else:
            role = getattr(m, "type", None) or "Other"
        transcript_lines.append(f"{role}: {m.content}")
    transcript = "\n".join(transcript_lines)

    try:
        ai = await llm.ainvoke([
            SystemMessage(content=_SUMMARY_SYSTEM_PROMPT),
            HumanMessage(content=transcript),
        ])
        text = ai.content if isinstance(ai.content, str) else str(ai.content)
        return text.strip() or "Session summary was empty."
    except Exception as exc:
        logger.warning("session summary failed (%s): falling back", exc)
        return f"Session summary unavailable due to LLM error: {exc}"



@dataclass
class BotContext:
    user_id:    str
    session_id: str
    log:        TurnLog
    llm:        Any                       # used by _summarize_history
    history:    list[Any] = field(default_factory=list)


async def dispatch_command(line: str, ctx: BotContext) -> bool:
    """run slash cmd, returns true if shutdown, false otherwise."""
    parts = line.split()
    cmd, args = parts[0], parts[1:]

    # `skip`
    if cmd == "/help":
        print(HELP_TEXT)
        return False

    if cmd == "/context":
        c = await build_context(user_id=ctx.user_id)
        print(c.as_prompt_block())
        return False

    if cmd == "/ctx":
        try:
            print(json.dumps(current_context.invoke({}), ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            print(f"  tool failed: {exc}")
        return False

    if cmd == "/calc":
        if not args:
            print("  usage: /calc <expression>")
            return False
        expr = " ".join(args)
        try:
            print(json.dumps(calculate_math.invoke({"expression": expr}), ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            print(f"  tool failed: {exc}")
        return False

    if cmd == "/time":
        if not args:
            print("  usage: /time [--tz <Zone>] <text>")
            return False
        timezone_arg: str | None = None
        text_parts = args
        if len(args) >= 2 and args[0] == "--tz":
            timezone_arg = args[1]
            text_parts = args[2:]
        text = " ".join(text_parts).strip()
        if not text:
            print("  usage: /time [--tz <Zone>] <text>")
            return False
        payload: dict[str, Any] = {"text": text}
        if timezone_arg:
            payload["timezone"] = timezone_arg
        try:
            print(json.dumps(resolve_relative_time.invoke(payload), ensure_ascii=False, indent=2, default=str))
        except Exception as exc:
            print(f"  tool failed: {exc}")
        return False

    if cmd == "/search":
        if not args:
            print("  usage: /search [--n <k>] <query>")
            return False
        n = 5
        query_parts = args
        if len(args) >= 2 and args[0] == "--n":
            if args[1].isdigit():
                n = int(args[1])
            query_parts = args[2:]
        query = " ".join(query_parts).strip()
        if not query:
            print("  usage: /search [--n <k>] <query>")
            return False
        try:
            result = web_search.invoke({"query": query, "max_results": n})
            print(_format_search(result if isinstance(result, dict) else {"results": result}))
        except Exception as exc:
            print(f"  tool failed: {exc}")
        return False

    if cmd == "/snapshot":
        print(await cmd_snapshot(ctx.user_id))
        return False

    if cmd == "/history":
        n = int(args[0]) if args and args[0].isdigit() else 10
        print(cmd_history(ctx.log, n))
        return False

    # mem lifecycle
    if cmd == "/flush":
        async def session_flush(_uid: str, _sid: str) -> None:
            # skip idle sweep
            if _uid == ctx.user_id and _sid == ctx.session_id:
                summary = await _summarize_history(ctx.llm, ctx.history)
            else:
                summary = (
                    f"Idle flush for {_sid}: transcript not owned by this "
                    "CLI process, summary unavailable."
                )
            mem_embedding = await _safe_embed(summary)
            mem_payload   = {
                "summary":    summary,
                "importance": 0.3,
                "user_id":    _uid,
                "session_id": _sid,
            }
            _log_kg_write("Memory", mem_payload, embedding=mem_embedding)
            mem_id = await write_memory(MemoryInput(
                **mem_payload,
                embedding=mem_embedding,
            ))
            _log_kg_write_result("Memory", mem_id)
        counters = await nc.run_idle_memory_flush(flush=session_flush, idle_minutes=60)
        print(json.dumps(counters))
        return False

    if cmd == "/decay":
        print(json.dumps(await run_memory_decay()))
        return False

    if cmd == "/sweep":
        print(await cmd_sweep())
        return False

    # buat ngehitung
    if cmd == "/facts":
        if not args:
            print("  usage: /facts <#turn|message_id>")
            return False
        print(await cmd_facts(ctx.log, args[0]))
        return False

    if cmd == "/node":
        if len(args) != 2:
            print("  usage: /node <Label> <node_id>")
            return False
        print(await cmd_node(args[0], args[1]))
        return False

    if cmd == "/update":
        if len(args) < 4:
            print("  usage: /update <Label> <node_id> <prop> <value>")
            return False
        label, node_id, prop = args[0], args[1], args[2]
        value_raw = " ".join(args[3:])
        try:
            print(await cmd_update(label, node_id, prop, value_raw))
        except ValueError as exc:
            print(f"  rejected: {exc}")
        return False

    if cmd == "/soft":
        if not args:
            print("  usage: /soft <#turn|message_id> [reason]")
            return False
        reason = " ".join(args[1:]) or "user_deleted_message"
        print(await cmd_soft(ctx.log, args[0], reason))
        return False

    if cmd == "/purge":
        if not args:
            print("  usage: /purge <#turn|message_id>")
            return False
        print(await cmd_purge(ctx.log, args[0]))
        return False

    if cmd == "/wipe-user":
        if not args:
            print("  usage: /wipe-user <user_id>")
            return False
        print(await cmd_wipe_user(args[0]))
        return False

    if cmd == "/supersede":
        if len(args) < 2:
            print("  usage: /supersede <thought_id> <new content>")
            return False
        old_thought_id = args[0]
        new_content    = " ".join(args[1:])
        print(await cmd_supersede(
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            old_thought_id=old_thought_id,
            new_content=new_content,
        ))
        return False

    # shut down.
    if cmd == "/end":
        # summarize user" "compress in-memory" "semantic retrieval
        if args:
            summary = " ".join(args)
        else:
            summary = await _summarize_history(ctx.llm, ctx.history)
        mem_embedding = await _safe_embed(summary)
        mem_payload   = {
            "summary":    summary,
            "importance": 0.6,
            "user_id":    ctx.user_id,
            "session_id": ctx.session_id,
        }
        _log_kg_write("Memory", mem_payload, embedding=mem_embedding)
        mem_id = await write_memory(MemoryInput(
            **mem_payload,
            embedding=mem_embedding,
        ))
        _log_kg_write_result("Memory", mem_id)
        print(f"Memory written: {mem_id}")
        return True

    print(f"Unknown command: {cmd}. Try /help.")
    return False



async def chat_loop(user_id: str, session_id: str) -> None:
    llm = _bind_tools_if_supported(_make_llm())
    history: list[Any] = []
    log = TurnLog()
    ctx = BotContext(
        user_id=user_id,
        session_id=session_id,
        log=log,
        llm=llm,
        history=history,
    )
    turn_index = 0

    print()
    print(f"Test bot ready. user_id={user_id} session_id={session_id}")
    print("Type a message, or /help for commands. Ctrl-D to quit.")
    print()
    turn = 0
    while True:
        try:
            print("=" * 100)
            line = input("you> ").strip()
            print("=" * 100)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        # `skip`
        if line.startswith("/"):
            try:
                shutdown = await dispatch_command(line, ctx)
            except Exception as exc:
                logger.exception("Command failed: %s", exc)
                print(f"  command error: {exc}")
                continue
            if shutdown:
                break
            continue

        # normal turn.
        turn_index += 1
        message_id = f"msg-{uuid.uuid4()}"

        # if _safe_embed() is None:     build_context()
        query_embedding = await _safe_embed(line)
        _log_pg_read(line, query_embedding)

        retrieved = await build_context(
            user_id=user_id,
            query_embedding=query_embedding,
        )
        print("Memory chat nih: ", retrieved)
        _log_kg_read_summary(retrieved)

        cbt_state = await _run_cbt_dialogue_policy({
            "user_text": line,
            "user_id": user_id,
            "session_id": session_id,
        })
        cbt_instruction = str(cbt_state.get("cbt_instruction") or "").strip()
        print("CBT BOS" + "==="*100)
        print(cbt_instruction)

        sys_msg   = SystemMessage(content=render_system_prompt(retrieved.as_prompt_block()))
        history.append(HumanMessage(content=line))

        # keep last_activity fresh
        await nc.get_client().execute_write(
            "MATCH (s:Session {id: $sid}) SET s.last_activity = datetime()",
            {"sid": session_id},
        )

        try:
            pre_msgs = [sys_msg]
            if cbt_instruction:
                pre_msgs.append(
                    SystemMessage(
                        content=f"CBT guidance for this turn:\n{cbt_instruction}"
                    )
                )
            ai = await _ainvoke_with_tools(llm, pre_msgs + history)
        except Exception as exc:
            logger.exception("LLM call failed: %s", exc)
            print(f"[bot error: {exc}]")
            continue

        parsed = parse_turn(ai.content if isinstance(ai.content, str) else str(ai.content))
        history.append(AIMessage(content=parsed.reply))

        web_urls = []
        kw = getattr(ai, "additional_kwargs", None)
        if isinstance(kw, dict) and isinstance(kw.get("web_search_urls"), list):
            web_urls = [u for u in kw["web_search_urls"] if isinstance(u, str) and u.strip()]

        reply_for_user = _append_references(parsed.reply, web_urls)

        print("=" * 100)
        print(f"bot> {reply_for_user}")
        print("=" * 100)

        node_ids: dict[str, str | None] = {}
        if parsed.kg:
            try:
                node_ids = await apply_kg_block(
                    parsed.kg,
                    user_id=user_id,
                    session_id=session_id,
                    message_id=message_id,
                )
                written = {k: v for k, v in node_ids.items() if v}
                if written:
                    logger.info("KG updated: %s", written)
            except Exception as exc:
                logger.exception("KG write failed: %s", exc)

        log.add(TurnRecord(
            index=turn_index,
            message_id=message_id,
            user_text=line,
            reply=parsed.reply,
            node_ids=node_ids,
        ))


async def chat_loop_nodes(
    user_id: str,
    session_id: str,
    *,
    trace_cbt: bool = False,
    trace_metadata: bool = False,
) -> None:
    """buat ngambil data"""
    llm = _bind_tools_if_supported(_make_llm())
    history: list[Any] = []
    log = TurnLog()
    ctx = BotContext(
        user_id=user_id,
        session_id=session_id,
        log=log,
        llm=llm,
        history=history,
    )

    state = _init_node_state(user_id=user_id, session_id=session_id)
    audit: GuardrailLogger = StdoutGuardrailLogger(
        enabled=trace_cbt,
        include_metadata=trace_metadata,
        only_cbt_and_memory=True,
    )
    turn_index = 0

    print()
    print(f"Test bot ready (pipeline=nodes). user_id={user_id} session_id={session_id}")
    if trace_cbt:
        print(f"Trace enabled: cbt/memory{' +metadata' if trace_metadata else ''}")
    print("Type a message, or /help for commands. Ctrl-D to quit.")
    print()

    while True:
        try:
            print("=" * 100)
            line = input("you> ").strip()
            print("=" * 100)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        if line.startswith("/"):
            try:
                shutdown = await dispatch_command(line, ctx)
            except Exception as exc:
                logger.exception("Command failed: %s", exc)
                print(f"  command error: {exc}")
                continue
            if shutdown:
                break
            continue

        turn_index += 1
        message_id = f"msg-{uuid.uuid4()}"

        # keep last_activity fresh
        try:
            await nc.get_client().execute_write(
                "MATCH (s:Session {id: $sid}) SET s.last_activity = datetime()",
                {"sid": session_id},
            )
        except Exception:
            pass

        _reset_turn_transients(state)
        state["current_message"] = line

        # run focused node pipeline
        try:
            state = await memory_retrieval_node(state, audit=audit)
            state = await dialogue_policy_node(state, audit=audit)
            state = await response_generator_node(state, llm=llm, audit=audit)
        except Exception as exc:
            logger.exception("Node pipeline failed: %s", exc)
            print(f"[bot error: {exc}]")
            continue

        # treat as final
        state["final_response"] = (state.get("response_draft") or "").strip() or None

        # append to transcript
        state = await session_end_node(state, audit=audit)
        # log: CBT
        kg_context = (state.get("kg_context") or "")
        directive = state.get("cbt_directive") or {}
        technique = state.get("cbt_node_active")
        reason = directive.get("reason")
        print(f"[memory] kg_context_chars={len(kg_context)}")
        print(f"[cbt] technique={technique} reason={reason}")

        reply = (state.get("final_response") or "").strip()
        if not reply:
            reply = "(empty reply)"

        history.append(HumanMessage(content=line))
        history.append(AIMessage(content=reply))

        print("=" * 100)
        print(f"bot> {reply}")
        print("=" * 100)

        log.add(TurnRecord(
            index=turn_index,
            message_id=message_id,
            user_text=line,
            reply=reply,
            node_ids={},
        ))



async def _bootstrap_user_and_session(user_id: str | None) -> tuple[str, str]:
    """if user, ok := db.Get("user").(map[string]interface{}) {     user["id"].(string) } if session, ok := db.Get("session").(map[string]interface{}) {     session["id"].(string) }"""
    client = nc.get_client()
    user_id    = user_id or f"cli-user-{uuid.uuid4()}"
    session_id = f"cli-sess-{uuid.uuid4()}"

    await client.execute_write(
        """
        MERGE (u:User {id: $user_id})
          ON CREATE SET u.name = 'CLI tester',
                        u.display_name = 'cli',
                        u.preferred_language = 'en',
                        u.created_at = datetime(),
                        u.consent_research = false,
                        u.active = true
        CREATE (s:Session {
            id:            $session_id,
            started_at:    datetime(),
            last_activity: datetime(),
            ended_at:      null,
            summary:       null,
            active:        true
        })
        CREATE (u)-[:HAD_SESSION {
            t_valid:        datetime(),
            t_invalid:      null,
            confidence:     1.0,
            source_session: $session_id
        }]->(s)
        """,
        {"user_id": user_id, "session_id": session_id},
    )
    return user_id, session_id


async def main(argv: list[str]) -> int:
    user_id_arg = None
    if "--user-id" in argv:
        idx = argv.index("--user-id")
        if idx + 1 < len(argv):
            user_id_arg = argv[idx + 1]

    pipeline = "legacy"
    if "--pipeline" in argv:
        idx = argv.index("--pipeline")
        if idx + 1 < len(argv):
            pipeline = (argv[idx + 1] or "").strip().lower() or "legacy"

    trace_cbt = "--trace-cbt" in argv
    trace_metadata = "--trace-metadata" in argv

    await nc.init_client()
    healthy = await nc.get_client().health_check()
    if not healthy:
        print("Neo4j not reachable. Set NEO4J_URI/USERNAME/PASSWORD.", file=sys.stderr)
        return 2

    user_id, session_id = await _bootstrap_user_and_session(user_id_arg)
    try:
        if pipeline in ("nodes", "mini", "cbt"):  # aliases
            await chat_loop_nodes(
                user_id,
                session_id,
                trace_cbt=trace_cbt,
                trace_metadata=trace_metadata,
            )
        else:
            await chat_loop(user_id, session_id)
    finally:
        # stamp ended_at & last_activity
        await nc.get_client().execute_write(
            """
            MATCH (s:Session {id: $sid})
            SET s.ended_at = datetime(), s.last_activity = datetime()
            """,
            {"sid": session_id},
        )
        await nc.close_client()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))

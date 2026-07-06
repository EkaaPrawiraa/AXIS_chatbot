"""Composes the prompt context block from three layers:."""

from __future__ import annotations

import logging
import os
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


logger = logging.getLogger(__name__)


SHORT_TERM_TURN_PAIRS: int = 4    # 4 user + 4 assistant = 8 messages
KG_CONTEXT_CHAR_BUDGET: int = 6000

# Retrieval-query construction (Option 1 + Option 3 hybrid):
#   1. Stitch the last N user turns + current message into one window so
#      anaphora and short replies carry their conversational referent.
#   2. Feed that window to a small OpenAI rewriter (RETRIEVAL_QUERY_REWRITER)
#      that emits one self-contained search query. The rewriter is
#      pinned to gpt-4o-mini-class temp=0.0 so it stays deterministic.
# Both steps are best-effort: the raw current_message is always the
# fallback if either step fails.
_RETRIEVAL_QUERY_USER_TURNS: int = 3
_RETRIEVAL_QUERY_MAX_CHARS: int = 1200


def _retrieval_rewrite_enabled() -> bool:
    return os.getenv("RETRIEVAL_QUERY_REWRITE_ENABLED", "1").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _build_retrieval_window(state: ConversationState) -> str:
    """Concatenate the last few user turns + current message.

    Output is a single string with ``|`` separators so the embedder
    (and the rewriter LLM upstream) can still recover turn boundaries
    cheaply. Bounded by ``_RETRIEVAL_QUERY_MAX_CHARS`` to keep the
    embedding from getting diluted on long sessions.
    """
    msgs = state.get("messages") or []
    user_msgs: list[str] = []
    for m in msgs[-(_RETRIEVAL_QUERY_USER_TURNS * 4):]:
        if isinstance(m, dict) and m.get("role") == "user":
            text = str(m.get("content") or "").strip()
            if text:
                user_msgs.append(text)
    user_msgs = user_msgs[-_RETRIEVAL_QUERY_USER_TURNS:]

    current = (state.get("current_message") or "").strip()
    if current:
        user_msgs.append(current)

    window = " | ".join(user_msgs).strip()
    if len(window) > _RETRIEVAL_QUERY_MAX_CHARS:
        window = window[-_RETRIEVAL_QUERY_MAX_CHARS:]
    return window


async def _rewrite_retrieval_query(window: str, language: str | None) -> str:
    """Call the small OpenAI rewriter to produce one self-contained query.

    Returns an empty string on any failure; caller must fall back to
    the raw window text.
    """
    if not window:
        return ""
    try:
        from agentic.config.llm_models import RETRIEVAL_QUERY_REWRITER, build_llm
        from agentic.prompts import load_prompt_bundle
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception as exc:  # pragma: no cover - import guards for tests
        logger.debug("retrieval rewriter unavailable: %s", exc)
        return ""

    try:
        bundle = load_prompt_bundle("nodes/retrieval_query_rewriter")
        system_text = bundle.system
        if language:
            system_text = (
                f"{system_text}\n\n"
                f"User's resolved language: {language}. Mirror it in the output."
            )
        llm = build_llm(RETRIEVAL_QUERY_REWRITER)
        ai = await llm.ainvoke(
            [
                SystemMessage(content=system_text),
                HumanMessage(
                    content=(
                        "Recent user turns (oldest first), separated by '|', "
                        "with the CURRENT message as the last segment:\n\n"
                        f"{window}\n\n"
                        "Rewrite into ONE self-contained search query "
                        "following the rules in the system prompt."
                    )
                ),
            ]
        )
        rewritten = str(getattr(ai, "content", "") or "").strip()
        # Strip common LLM artefacts: surrounding quotes, "Query:" prefix.
        if rewritten.lower().startswith("query:"):
            rewritten = rewritten.split(":", 1)[1].strip()
        rewritten = rewritten.strip("\"' \t")
        # Single line only.
        if "\n" in rewritten:
            rewritten = rewritten.split("\n", 1)[0].strip()
        return rewritten
    except Exception as exc:
        logger.warning("retrieval rewrite failed: %s", exc)
        return ""



class ContextBuilderFn:
    """
    Protocol for the context builder. Production wires
    ``agentic.memory.context_builder.build_context``; tests pass a
    fake that returns a pre-baked block.
    """

    async def __call__(
        self,
        *,
        user_id: str,
        session_id: str,
        query: str,
        language: str | None,
    ) -> str:
        ...


@dataclass(frozen=True)
class ContextStats:
    long_term_chars: int
    short_term_chars: int
    truncated: bool


def _format_short_term(state: ConversationState) -> str:
    """Return a compact transcript of the last few turn pairs."""
    history = state.get("messages") or []
    if not history:
        return ""
    take = SHORT_TERM_TURN_PAIRS * 2
    tail = list(history)[-take:]
    rendered: list[str] = []
    for msg in tail:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            rendered.append(f"User: {content}")
        elif role == "assistant":
            rendered.append(f"Assistant: {content}")
        else:
            rendered.append(f"{role.title() if role else 'Other'}: {content}")
    if not rendered:
        return ""
    return "=== Short-term memory context ===\n" + "\n".join(rendered)


def _truncate(text: str, budget: int) -> tuple[str, bool]:
    if len(text) <= budget:
        return text, False
    truncated = text[: budget - 3].rstrip() + "..."
    return truncated, True



async def memory_retrieval_node(
    state: ConversationState,
    *,
    context_builder: ContextBuilderFn | None = None,
    audit: GuardrailLogger | None = None,
) -> ConversationState:
    """
    Populate ``state["kg_context"]`` for the response generator.

    Skipped when crisis is flagged (escalation owns the reply) or when
    PHQ-9 is mid administration (the questionnaire owns the turn).
    """
    audit = audit or NullGuardrailLogger()

    if state.get("safety_flag") == "crisis":
        return state

    phq9_phase = (state.get("phq9_state") or {}).get("phase", "idle")
    if phq9_phase in ("offered", "in_progress", "awaiting_clar"):
        return state

    started = time.perf_counter()
    long_term_block = ""

    if context_builder is None:
        context_builder = _default_context_builder()

    if context_builder is not None:
        # Build the retrieval query: concatenation window (Option 1) +
        # optional LLM rewrite into a self-contained query (Option 3).
        # Raw current_message is the deterministic fallback if either
        # step fails or produces empty output.
        raw_current = state.get("current_message") or ""
        retrieval_query = raw_current
        window = _build_retrieval_window(state)
        if window:
            retrieval_query = window
            if _retrieval_rewrite_enabled():
                rewritten = await _rewrite_retrieval_query(
                    window,
                    state.get("resolved_language"),
                )
                if rewritten:
                    retrieval_query = rewritten
                    logger.debug(
                        "retrieval query rewritten len=%d -> %d",
                        len(window), len(rewritten),
                    )
        try:
            long_term_block = await context_builder(
                user_id=state.get("user_id") or "",
                session_id=state.get("session_id") or "",
                query=retrieval_query,
                language=state.get("resolved_language"),
            ) or ""
        except Exception as exc:
            logger.warning("memory retrieval failed: %s", exc)
            long_term_block = ""

    short_term_block = _format_short_term(state)

    parts = [p for p in (long_term_block.strip(), short_term_block.strip()) if p]
    combined = "\n\n".join(parts)
    rendered, truncated = _truncate(combined, KG_CONTEXT_CHAR_BUDGET)

    state["kg_context"] = rendered or None
    # Structured retrieval context (Phase 1/2): populated by the default bridge
    # via _BridgeWithMeta.last_retrieval_context_dict; None for test bridges.
    state["retrieval_context"] = getattr(
        context_builder, "last_retrieval_context_dict", None
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.KG_ACCESS,
            event_type="memory_retrieved",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=("truncated" if truncated else None),
            latency_ms=elapsed_ms,
            metadata={
                "long_term_chars": len(long_term_block or ""),
                "short_term_chars": len(short_term_block or ""),
                "truncated": truncated,
                "ranked_candidates": len(
                    (state.get("retrieval_context") or {}).get("focused_recall", [])
                ),
            },
        )
    )
    return state



def _default_context_builder() -> ContextBuilderFn | None:
    """
    Lazily import the production context builder. Returns None when
    the import fails (test sandbox without Neo4j / pgvector clients);
    callers then pass an explicit builder.

    Returns a _BridgeWithMeta instance so memory_retrieval_node can read
    ``last_retrieval_context_dict`` after each call without changing the
    ContextBuilderFn str-return protocol (backward compat for test stubs).
    """
    if os.getenv("AGENTIC_DISABLE_CONTEXT_BUILDER"):
        return None
    try:
        from agentic.memory.context_builder import build_context  # type: ignore

        try:
            from agentic.memory.pg_vector import embed_text  # type: ignore
        except Exception:  # pragma: no cover
            embed_text = None  # type: ignore[assignment]

        class _BridgeWithMeta:
            """Callable bridge that exposes last retrieval_context_dict as an attr."""

            last_retrieval_context_dict: dict | None = None

            async def __call__(
                self,
                *,
                user_id: str,
                session_id: str,
                query: str,
                language: str | None,
            ) -> str:
                del session_id, language  # reserved for future builder upgrades
                query_embedding = None
                if embed_text is not None and query and query.strip():
                    try:
                        query_embedding = await embed_text(query)
                    except Exception:
                        query_embedding = None

                ctx = await build_context(
                    user_id=user_id,
                    query_embedding=query_embedding,
                    query_text=query,
                )
                self.last_retrieval_context_dict = getattr(
                    ctx, "retrieval_context_dict", None
                )
                if hasattr(ctx, "as_prompt_block"):
                    return ctx.as_prompt_block()
                return str(ctx) if ctx else ""

        return _BridgeWithMeta()
    except Exception as exc:  # pragma: no cover
        logger.debug("context_builder default bridge unavailable: %s", exc)
        return None


__all__ = [
    "memory_retrieval_node",
    "ContextBuilderFn",
    "SHORT_TERM_TURN_PAIRS",
    "KG_CONTEXT_CHAR_BUDGET",
]

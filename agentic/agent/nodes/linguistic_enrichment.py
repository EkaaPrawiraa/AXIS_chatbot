"""enrich node"""

from __future__ import annotations

import logging
import time
from typing import Any

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.linguistic import (
    LinguisticCorpus,
    detect_linguistic_signals,
    load_default_corpus,
)
from agentic.agent.state import ConversationState


logger = logging.getLogger(__name__)



async def linguistic_enrichment_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    corpus: LinguisticCorpus | None = None,
) -> ConversationState:
    """detect lang, surface slang, corpus"""
    audit = audit or NullGuardrailLogger()
    started = time.perf_counter()

    text = (state.get("current_message") or "").strip()
    if not text:
        # skip
        return state

    active_corpus = corpus if corpus is not None else load_default_corpus()
    fallback_lang = (
        state.get("resolved_language")
        or state.get("language_pref")
        or "id"
    )

    signals = detect_linguistic_signals(
        text, active_corpus, language_fallback=fallback_lang
    )
    state["linguistic_signals"] = signals.to_dict()  # type: ignore[typeddict-item]

    # refresh resolved_language, keep single-code, preserve code-switching.
    if signals.language == "mixed":
        # prefer indonesian base response lan downstream prompts must preserve natural mix.
        state["resolved_language"] = (
            state.get("language_pref")
            or state.get("resolved_language")
            or "id"
        )
    else:
        state["resolved_language"] = signals.language

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    await _audit_decision(audit, state, signals, elapsed_ms)
    return state



async def _audit_decision(
    audit: GuardrailLogger,
    state: ConversationState,
    signals: Any,
    latency_ms: int,
) -> None:
    severity = (
        GuardrailEventSeverity.WARN
        if signals.escalation_terms
        else GuardrailEventSeverity.INFO
    )
    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.INPUT,
            event_type="linguistic_enrichment",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=severity,
            trigger_detail=signals.language_signal,
            latency_ms=latency_ms,
            metadata={
                "language": signals.language,
                "register": signals.register,
                "slang_terms": list(signals.slang_terms[:10]),
                "distress_terms": list(signals.distress_terms),
                "escalation_terms": list(signals.escalation_terms),
                "id_tokens": signals.id_token_count,
                "en_tokens": signals.en_token_count,
                "total_tokens": signals.total_tokens,
            },
        )
    )


__all__ = ["linguistic_enrichment_node"]

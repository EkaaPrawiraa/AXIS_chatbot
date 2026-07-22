"""script"""

from __future__ import annotations

import logging
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
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.state import (
    ConversationState,
    TTSModelChoice,
    empty_voice_state,
)
from agentic.config.llm_models import (
    SPEECH_ADAPTER,
    SPEECH_ADAPTER_V3,
    LLMSpec,
    build_llm,
)
from agentic.gateway.monitoring import observe_langchain_usage


logger = logging.getLogger(__name__)


# v3 pre-render, audio, scripts, grounding, breathing, meditation, prosodic cues, conversational
V3_TECHNIQUES: frozenset[str] = frozenset(
    {
        CBTTechnique.GROUNDING.value,
    }
)


# skip


try:  # pragma: no cover
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover - sandbox fallback
    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"



def select_mode(state: ConversationState) -> TTSModelChoice:
    """v3 atau v2.5"""
    technique = state.get("cbt_node_active") or ""
    if technique in V3_TECHNIQUES:
        return "v3"
    return "v2_5_turbo"


def _select_spec(mode: TTSModelChoice) -> LLMSpec:
    return SPEECH_ADAPTER_V3 if mode == "v3" else SPEECH_ADAPTER


def _safe_fallback(text: str) -> str:
    """adapt fail llm"""
    out = text.strip()
    out = out.replace(" — ", " ")
    out = out.replace("—", " ")
    out = out.replace("- ", "")
    return out



async def speech_adapter_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    llm_v25: Any | None = None,
    llm_v3: Any | None = None,
) -> ConversationState:
    """buat nyimpan set tts_model"""
    audit = audit or NullGuardrailLogger()
    voice = dict(state.get("voice_state") or empty_voice_state())

    if voice.get("output_modality") not in ("voice", "both"):
        # skip
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    if voice.get("speech_adapted_in_generator"):
        # skip pass
        return state

    source_text = (state.get("final_response") or state.get("response_draft") or "").strip()
    if not source_text:
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    mode = select_mode(state)
    spec = _select_spec(mode)
    llm = (llm_v3 if mode == "v3" else llm_v25) or build_llm(spec)

    started = time.perf_counter()
    adapted: str | None = None
    try:
        language_context = _language_context(state)
        human_payload = (
            "TEKS SUMBER (rewrite-only; jangan menambah info; jangan ubah perspektif):\n"
            f"{language_context}\n"
            "---BEGIN SOURCE---\n"
            f"{source_text}\n"
            "---END SOURCE---"
        )
        ai = await llm.ainvoke(
            [
                _SystemMessage(content=spec.system_prompt),
                _HumanMessage(content=human_payload),
            ]
        )
        # print(human, ai)
        observe_langchain_usage(ai, fallback_model=spec.model)
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
        adapted = (raw or "").strip()
    except Exception as exc:
        logger.warning("speech adapter LLM failed: %s", exc)
        voice["voice_error"] = f"adapter_error:{exc}"

    if not adapted:
        adapted = _safe_fallback(source_text)
    adapted = _normalize_laughter(adapted)

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if mode == "v3":
        voice["speech_response_tags"] = adapted
        # skip enc
        voice["speech_response"] = _strip_v3_tags(adapted)
    else:
        voice["speech_response"] = adapted

    voice["tts_model"] = mode
    state["voice_state"] = voice  # type: ignore[typeddict-item]

    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,
            event_type=f"speech_adapted_{mode}",
            decision=GuardrailEventDecision.LOG_ONLY,
            severity=GuardrailEventSeverity.INFO,
            trigger_detail=state.get("cbt_node_active") or "default",
            latency_ms=elapsed_ms,
            metadata={
                "input_chars": len(source_text),
                "output_chars": len(adapted),
            },
        )
    )
    return state


# tag_scrub()


import re

_V3_TAG_RE = re.compile(r"\[[a-zA-Z][^\]]{0,32}\]")
_INDONESIAN_LAUGH_RE = re.compile(r"\b(?:w\s*k\s*){2,}|\b(?:k\s*w\s*){2,}|\b(?:x\s*i\s*){2,}", re.IGNORECASE)


def _strip_v3_tags(text: str) -> str:
    return _V3_TAG_RE.sub("", text).strip()


def _normalize_laughter(text: str) -> str:
    return _INDONESIAN_LAUGH_RE.sub("hahaha", text)


def _language_context(state: ConversationState) -> str:
    signals = state.get("linguistic_signals") or {}
    signal_language = signals.get("language") if isinstance(signals, dict) else None
    current_message = (state.get("current_message") or "").strip()
    resolved = state.get("resolved_language")
    preference = state.get("language_pref")
    return (
        "LANGUAGE POLICY (mandatory): Mirror the user's language exactly.\n"
        "1. If the user used English, keep the rewritten speech in English.\n"
        "2. If the user used Indonesian, keep it in Indonesian.\n"
        "3. If the user code-switched or mixed Indonesian and English, preserve"
        "the same natural mix and do not translate it into only one language. \n"
        "4. If the latest_user_message is empty, Use source text instead as user's language.\n"
        f"resolved_language={resolved or 'unknown'}; \n"
        f"language_pref={preference or 'unknown'}; \n"
        f"detected_user_language={signal_language or 'unknown'}; \n"
        f"latest_user_message={current_message!r}\n"
    )


__all__ = [
    "V3_TECHNIQUES",
    "select_mode",
    "speech_adapter_node",
]

"""validate"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import yaml

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    GuardrailEventDecision,
    GuardrailEventLayer,
    GuardrailEventSeverity,
    GuardrailLogger,
    NullGuardrailLogger,
)
from agentic.agent.state import ConversationState
from agentic.config.llm_models import GUARDRAIL_REWRITE, build_llm
from agentic.gateway.monitoring import observe_langchain_usage
from agentic.prompts import load_prompt, load_prompt_bundle


logger = logging.getLogger(__name__)


_WRAPPING_TRIPLE_QUOTES_RE = re.compile(r'^\s*"{3}\s*(.*?)\s*"{3}\s*$', re.DOTALL)


def _sanitize_user_output(text: str) -> str:
    cleaned = (text or "").strip()
    match = _WRAPPING_TRIPLE_QUOTES_RE.match(cleaned)
    if match:
        cleaned = match.group(1).strip()
    cleaned = re.sub(r"\s*[—–]\s*", " - ", cleaned)
    return re.sub(r"[ \t]{2,}", " ", cleaned)



@dataclass(frozen=True)
class PostGenRules:
    diagnostic_patterns: tuple[re.Pattern[str], ...]
    clinical_patterns: tuple[re.Pattern[str], ...]
    rewrite_instruction: str
    max_attempts: int


_POSTGEN_CACHE: PostGenRules | None = None


def load_postgen_rules(*, force_reload: bool = False) -> PostGenRules:
    global _POSTGEN_CACHE
    if _POSTGEN_CACHE is not None and not force_reload:
        return _POSTGEN_CACHE

    bundle = load_prompt_bundle("guardrails/post_generation")
    instruction_text = bundle.system

    # parse
    parsed = _parse_yaml_tail(instruction_text)

    diagnostic = tuple(
        re.compile(p, re.IGNORECASE)
        for p in parsed.get("DIAGNOSTIC_PATTERNS", [])
    )
    clinical = tuple(
        re.compile(p, re.IGNORECASE)
        for p in parsed.get("CLINICAL_INSTRUCTION_PATTERNS", [])
    )
    max_attempts = int(parsed.get("MAX_REWRITE_ATTEMPTS", 2))

    _POSTGEN_CACHE = PostGenRules(
        diagnostic_patterns=diagnostic,
        clinical_patterns=clinical,
        rewrite_instruction=instruction_text,
        max_attempts=max_attempts,
    )
    return _POSTGEN_CACHE


def _parse_yaml_tail(text: str) -> dict[str, Any]:
    """parse as yaml, fail -> extract first valid."""
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except yaml.YAMLError:
        pass
    # diagnostic_patterns
    marker = "DIAGNOSTIC_PATTERNS:"
    idx = text.find(marker)
    if idx == -1:
        return {}
    try:
        return yaml.safe_load(text[idx:]) or {}
    except yaml.YAMLError as exc:
        logger.warning("post_generation YAML tail parse failed: %s", exc)
        return {}



@dataclass(frozen=True)
class OutputViolation:
    pattern: str
    category: str  # "diagnostic" | "clinical_instruction"


def find_violations(
    draft: str, rules: PostGenRules | None = None
) -> tuple[OutputViolation, ...]:
    rules = rules or load_postgen_rules()
    if not draft:
        return ()
    out: list[OutputViolation] = []
    for p in rules.diagnostic_patterns:
        if p.search(draft):
            out.append(OutputViolation(pattern=p.pattern, category="diagnostic"))
    for p in rules.clinical_patterns:
        if p.search(draft):
            out.append(
                OutputViolation(pattern=p.pattern, category="clinical_instruction")
            )
    return tuple(out)



# re-use fallback msg
try:  # pragma: no cover - import behavior depends on environment
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover - fallback path
    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"


async def _request_rewrite(
    *,
    draft: str,
    instruction: str,
    llm: Any,
    language_hint: str = "",
) -> str:
    """llm call"""
    prefix = (
        f"Language preservation (mandatory): {language_hint}\n\n"
        if language_hint
        else ""
    )
    user_payload = (
        prefix
        + "Original draft:\n"
        + '"""\n'
        + f"{draft}\n"
        + '"""\n\n'
        + "Rewrite the draft following the policy."
    )
    try:
        ai = await llm.ainvoke(
            [
                _SystemMessage(content=instruction),
                _HumanMessage(content=user_payload),
            ]
        )
        observe_langchain_usage(ai, fallback_model=getattr(llm, "model_name", None))
        text = ai.content if isinstance(ai.content, str) else str(ai.content)
        return text.strip()
    except Exception as exc:
        logger.warning("guardrail rewrite LLM failed: %s", exc)
        return ""


def _safe_fallback() -> str:
    return load_prompt("guardrails/safe_fallback")


def _empty_response_fallback(state: ConversationState) -> str:
    language = (
        state.get("resolved_language")
        or state.get("language_pref")
        or (state.get("phq9_state") or {}).get("language")
        or "id"
    )
    if language == "en":
        return "I'm here with you. Could you send that once more so I can respond properly?"
    return "Aku tetap di sini. Bisa kirim sekali lagi supaya aku bisa merespons dengan tepat?"


def _language_preservation_hint(state: ConversationState) -> str:
    signals = state.get("linguistic_signals") or {}
    detected = None
    if isinstance(signals, dict):
        detected = signals.get("language")
    base = state.get("resolved_language") or state.get("language_pref") or "id"
    if detected == "mixed":
        return (
            "The original draft is code-switched (mixed). Preserve the same natural mix; "
            "do NOT translate into a single language."
        )
    if detected == "en" or str(base).lower().startswith("en"):
        return "Keep the response in English. Do NOT translate it to Indonesian."
    if detected == "id" or str(base).lower().startswith("id"):
        return "Keep the response in Indonesian. Do NOT translate it to English."
    return "Preserve the original language of the draft; do not translate."



async def output_guardrail_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    rewrite_llm: Any | None = None,
    rules: PostGenRules | None = None,
) -> ConversationState:
    """skip if final resp exists"""
    audit = audit or NullGuardrailLogger()

    if state.get("crisis_escalated"):  # type: ignore[typeddict-unknown-key]
        return state

    draft = _sanitize_user_output(state.get("response_draft") or "")
    if not draft:
        if not _sanitize_user_output(state.get("final_response") or ""):
            state["final_response"] = _empty_response_fallback(state)
            await audit.log(
                GuardrailEvent(
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    layer=GuardrailEventLayer.POST_GEN,
                    event_type="empty_response_fallback",
                    decision=GuardrailEventDecision.FALLBACK,
                    severity=GuardrailEventSeverity.WARN,
                )
            )
        return state
    state["response_draft"] = draft

    rules = rules or load_postgen_rules()
    started = time.perf_counter()

    violations = find_violations(draft, rules=rules)
    if not violations:
        # audit pass rate.
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        state["final_response"] = draft
        await audit.log(
            GuardrailEvent(
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
                layer=GuardrailEventLayer.POST_GEN,
                event_type="output_clean",
                decision=GuardrailEventDecision.ALLOW,
                severity=GuardrailEventSeverity.INFO,
                latency_ms=elapsed_ms,
            )
        )
        return state

    llm = rewrite_llm if rewrite_llm is not None else build_llm(GUARDRAIL_REWRITE)
    attempts = 0
    current_draft = draft

    while attempts < rules.max_attempts:
        attempts += 1
        rewritten = await _request_rewrite(
            draft=current_draft,
            instruction=rules.rewrite_instruction,
            llm=llm,
            language_hint=_language_preservation_hint(state),
        )
        if not rewritten:
            # count, max, empty, fallback, break, first, exhausted.
            logger.warning(
                "guardrail rewrite attempt %d/%d returned empty string; continuing",
                attempts,
                rules.max_attempts,
            )
            continue

        rewritten = _sanitize_user_output(rewritten)
        new_violations = find_violations(rewritten, rules=rules)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if not new_violations:
            state["final_response"] = rewritten
            await audit.log(
                GuardrailEvent(
                    user_id=state.get("user_id"),
                    session_id=state.get("session_id"),
                    layer=GuardrailEventLayer.POST_GEN,
                    event_type="rewrite_success",
                    decision=GuardrailEventDecision.REWRITE,
                    severity=GuardrailEventSeverity.WARN,
                    trigger_detail=violations[0].pattern[:80],
                    latency_ms=elapsed_ms,
                    metadata={
                        "attempts": attempts,
                        "categories": sorted({v.category for v in violations}),
                    },
                )
            )
            return state

        current_draft = rewritten

    # skip error
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    state["final_response"] = _safe_fallback()
    await audit.log(
        GuardrailEvent(
            user_id=state.get("user_id"),
            session_id=state.get("session_id"),
            layer=GuardrailEventLayer.POST_GEN,
            event_type="safe_fallback",
            decision=GuardrailEventDecision.FALLBACK,
            severity=GuardrailEventSeverity.CRITICAL,
            trigger_detail=violations[0].pattern[:80],
            latency_ms=elapsed_ms,
            metadata={
                "attempts": attempts,
                "categories": sorted({v.category for v in violations}),
            },
        )
    )
    return state


__all__ = [
    "PostGenRules",
    "OutputViolation",
    "load_postgen_rules",
    "find_violations",
    "output_guardrail_node",
]

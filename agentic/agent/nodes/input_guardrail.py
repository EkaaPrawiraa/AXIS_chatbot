"""Layer 2 input validation."""

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
from agentic.prompts import load_prompt_bundle


logger = logging.getLogger(__name__)



@dataclass(frozen=True)
class InputDecision:
    decision: str            # "allow" | "block" | "escalate_crisis"
    reason: str
    matched: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "matched": self.matched,
        }



@dataclass(frozen=True)
class InputRules:
    # Each keyword is pre-compiled as a word-boundary pattern.
    # Using compiled patterns instead of raw strings keeps evaluate_input()
    # free of per-call compilation overhead and makes the boundary logic
    # a single point of truth.
    crisis_keywords_id: tuple[re.Pattern[str], ...]
    crisis_keywords_en: tuple[re.Pattern[str], ...]
    jailbreak_patterns: tuple[re.Pattern[str], ...]
    off_scope_patterns: tuple[re.Pattern[str], ...]


# Character class covering Latin + extended Latin (covers Indonesian,
# most European loanwords, and common diacritics). Used as the
# word-boundary anchor so the pattern does not rely on \\b, which
# treats accented chars as non-word in some Python/ICU configurations.
_LETTER = r"[A-Za-zÀ-ɏḀ-ỿ]"
_BOUND_PRE = rf"(?<!{_LETTER})"
_BOUND_POST = rf"(?!{_LETTER})"


def _compile_keyword(kw: str) -> re.Pattern[str]:
    """
    Compile a crisis keyword with Unicode-aware word boundaries.

    A keyword matches only when it is not immediately preceded or
    followed by a letter character. This prevents "mati" from
    matching "matematika" while still matching "mati lah" or
    "pengen mati".
    """
    return re.compile(
        _BOUND_PRE + re.escape(kw.lower()) + _BOUND_POST,
        re.IGNORECASE,
    )


_RULES_CACHE: InputRules | None = None


def load_input_rules(*, force_reload: bool = False) -> InputRules:
    """Read and parse guardrails/input_validation.yaml."""
    global _RULES_CACHE
    if _RULES_CACHE is not None and not force_reload:
        return _RULES_CACHE

    bundle = load_prompt_bundle("guardrails/input_validation")
    # The "system" block is YAML-shaped text. Parse it as YAML to
    # extract the structured lists. This keeps a single editable YAML
    # file rather than mixing prose and structure.
    try:
        parsed = yaml.safe_load(bundle.system) or {}
    except yaml.YAMLError as exc:
        raise ValueError(
            f"input_validation system block is not valid YAML: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            "input_validation system block must parse to a mapping"
        )

    crisis_id = list(parsed.get("CRISIS_KEYWORDS_ID") or [])
    crisis_en = list(parsed.get("CRISIS_KEYWORDS_EN") or [])
    raw_jailbreak = list(parsed.get("JAILBREAK_PATTERNS") or [])
    raw_off_scope = list(parsed.get("OFF_SCOPE_PATTERNS") or [])

    if not crisis_id:
        logger.warning(
            "input_validation: CRISIS_KEYWORDS_ID list is empty; "
            "Indonesian crisis detection will not fire. Check guardrails/input_validation.yaml."
        )
    if not crisis_en:
        logger.warning(
            "input_validation: CRISIS_KEYWORDS_EN list is empty; "
            "English crisis detection will not fire. Check guardrails/input_validation.yaml."
        )

    _RULES_CACHE = InputRules(
        crisis_keywords_id=tuple(_compile_keyword(k) for k in crisis_id),
        crisis_keywords_en=tuple(_compile_keyword(k) for k in crisis_en),
        jailbreak_patterns=tuple(re.compile(p, re.IGNORECASE) for p in raw_jailbreak),
        off_scope_patterns=tuple(re.compile(p, re.IGNORECASE) for p in raw_off_scope),
    )
    return _RULES_CACHE



def evaluate_input(message: str, rules: InputRules | None = None) -> InputDecision:
    """
    Evaluate one user message. Crisis takes precedence over jailbreak;
    jailbreak takes precedence over allow.

    Crisis keywords are matched with word-boundary anchors (see module
    docstring) so substrings inside longer words do not trigger false
    positives. Jailbreak patterns already use full regex and are
    unchanged.
    """
    rules = rules or load_input_rules()
    if not message:
        return InputDecision(decision="allow", reason="empty_message")

    for pat in rules.crisis_keywords_id:
        m = pat.search(message)
        if m:
            return InputDecision(
                decision="escalate_crisis",
                reason="crisis_keyword_id",
                matched=m.group(0),
            )
    for pat in rules.crisis_keywords_en:
        m = pat.search(message)
        if m:
            return InputDecision(
                decision="escalate_crisis",
                reason="crisis_keyword_en",
                matched=m.group(0),
            )

    for pat in rules.jailbreak_patterns:
        m = pat.search(message)
        if m:
            return InputDecision(
                decision="block",
                reason="jailbreak_pattern",
                matched=m.group(0)[:120],
            )

    # Off-scope deliverable requests.
    # Crisis and jailbreak take precedence; off-scope is the lowest-
    # priority block so a distress signal embedded in a coding request
    # still routes to the crisis path.
    for pat in rules.off_scope_patterns:
        m = pat.search(message)
        if m:
            return InputDecision(
                decision="block",
                reason="off_scope",
                matched=m.group(0)[:120],
            )

    return InputDecision(decision="allow", reason="ok")



_OFF_SCOPE_REFUSAL_ID = (
    "Aku nggak bisa mengerjakan tugas atau deliverable itu langsung. "
    "Tapi aku bisa bantu kamu memecahnya jadi langkah kecil, memahami "
    "bagian yang bikin macet, atau nemenin kamu mulai pelan-pelan."
)

_OFF_SCOPE_REFUSAL_EN = (
    "I can't complete that task or deliverable for you directly. But I can "
    "help you break it into smaller steps, understand where you're stuck, "
    "or stay with you while you start slowly."
)


def _off_scope_refusal_text(state: ConversationState) -> str:
    signals = state.get("linguistic_signals") or {}
    detected = signals.get("language") if isinstance(signals, dict) else None
    language = (
        detected
        or state.get("resolved_language")
        or state.get("language_pref")
        or "id"
    )
    if str(language).lower().startswith("en"):
        return _OFF_SCOPE_REFUSAL_EN
    return _OFF_SCOPE_REFUSAL_ID


async def input_guardrail_node(
    state: ConversationState,
    *,
    audit: GuardrailLogger | None = None,
    rules: InputRules | None = None,
) -> ConversationState:
    """Layer 2 entry-point node."""
    audit = audit or NullGuardrailLogger()
    started = time.perf_counter()

    message = state.get("current_message") or ""
    verdict = evaluate_input(message, rules=rules)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    state["input_guardrail"] = verdict.to_dict()

    # Off-scope refusal is fully deterministic — write the response now
    # so the graph can short-circuit the LLM-bearing nodes downstream.
    # crisis_escalated tells output_guardrail to pass through unchanged.
    if verdict.decision == "block" and verdict.reason == "off_scope":
        state["final_response"] = _off_scope_refusal_text(state)
        state["crisis_escalated"] = True

    if verdict.decision != "allow":
        decision_enum = (
            GuardrailEventDecision.ESCALATE
            if verdict.decision == "escalate_crisis"
            else GuardrailEventDecision.BLOCK
        )
        severity = (
            GuardrailEventSeverity.CRITICAL
            if verdict.decision == "escalate_crisis"
            else GuardrailEventSeverity.WARN
        )
        await audit.log(
            GuardrailEvent(
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
                layer=GuardrailEventLayer.INPUT,
                event_type=verdict.reason,
                decision=decision_enum,
                severity=severity,
                trigger_detail=verdict.matched,
                latency_ms=elapsed_ms,
            )
        )
    return state


__all__ = [
    "InputDecision",
    "InputRules",
    "evaluate_input",
    "input_guardrail_node",
    "load_input_rules",
]

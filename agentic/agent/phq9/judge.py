"""Hybrid judge for PHQ-9 item responses."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from agentic.assessment.phq9 import item_text, options_with_scores
from agentic.config.llm_models import PHQ9_JUDGE, build_llm
from agentic.gateway.monitoring import observe_langchain_usage


logger = logging.getLogger(__name__)


# Message classes (langchain or fallback)


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



class JudgeAction(str, Enum):
    ADVANCE = "advance"
    CLARIFY = "clarify"
    BACK = "back"
    DECLINE = "decline"
    STOP = "stop"


@dataclass(frozen=True)
class JudgeOutcome:
    """Parsed structured output from the judge."""

    score: int
    confidence: float
    action: JudgeAction
    next_item: int | None
    rationale: str
    raw: str

    @property
    def is_actionable(self) -> bool:
        """True when the outcome can be applied without clarification."""
        return self.action in (JudgeAction.ADVANCE, JudgeAction.BACK)


# Rule-based scorer


# Confidence threshold above which the rule-based score is accepted
# without asking the LLM to re-score. The LLM is still called for the
# routing decision (action / next_item / rationale).
RULE_CONFIDENCE_THRESHOLD: float = 0.90

# Canonical option map — Indonesian (id).
# Keys are lowercased and stripped of trailing punctuation.
_OPTION_MAP_ID: dict[str, int] = {
    # Score 0 — Tidak sama sekali
    "tidak sama sekali": 0,
    "tidak": 0,
    "ga sama sekali": 0,
    "enggak sama sekali": 0,
    "gak sama sekali": 0,
    "nggak sama sekali": 0,
    "engga sama sekali": 0,
    "ngga sama sekali": 0,
    "ga pernah": 0,
    "tidak pernah": 0,
    "belum pernah": 0,
    # Score 1 — Beberapa hari
    "beberapa hari": 1,
    "beberapa": 1,
    "kadang": 1,
    "sesekali": 1,
    "sekali-sekali": 1,
    "jarang": 1,
    "terkadang": 1,
    "kadang-kadang": 1,
    # Score 2 — Lebih dari setengah hari
    "lebih dari setengah hari": 2,
    "lebih dari setengah": 2,
    "sering": 2,
    "cukup sering": 2,
    "lumayan sering": 2,
    "hampir sering": 2,
    # Score 3 — Hampir setiap hari
    "hampir setiap hari": 3,
    "hampir setiap saat": 3,
    "setiap hari": 3,
    "selalu": 3,
    "terus-terusan": 3,
    "terus menerus": 3,
    "sepanjang waktu": 3,
    "tiap hari": 3,
}

# Canonical option map — English (en).
_OPTION_MAP_EN: dict[str, int] = {
    # Score 0 — Not at all
    "not at all": 0,
    "not really": 0,
    "no": 0,
    "never": 0,
    "nope": 0,
    "nah": 0,
    "none": 0,
    "zero": 0,
    # Score 1 — Several days
    "several days": 1,
    "some days": 1,
    "sometimes": 1,
    "occasionally": 1,
    "a few days": 1,
    "a couple of days": 1,
    "here and there": 1,
    "once in a while": 1,
    # Score 2 — More than half the days
    "more than half the days": 2,
    "more than half": 2,
    "often": 2,
    "most days": 2,
    "frequently": 2,
    "a lot": 2,
    "pretty often": 2,
    # Score 3 — Nearly every day
    "nearly every day": 3,
    "almost every day": 3,
    "every day": 3,
    "always": 3,
    "all the time": 3,
    "daily": 3,
    "constantly": 3,
    "every single day": 3,
    "non-stop": 3,
}

_DIGIT_RE = re.compile(r"^\s*([0-3])\s*$")
_PUNCT_TAIL_RE = re.compile(r"[.,!?؟]+$")
_MULTI_SPACE_RE = re.compile(r"\s+")

# Cap on how many extra words are tolerated after a canonical label match
# (e.g. "kadang deh" / "kadang sih" are still a direct pick). Without this
# cap, `normalized.startswith(label)` would also match a long free-text
# sentence that merely happens to OPEN with a common word that is also a
# canonical label ("kadang", "sering", "jarang", "selalu", "tidak" are all
# ordinary Indonesian sentence-openers). That previously let a nuanced
# multi-sentence answer get silently scored off its first word alone —
# dangerous on item 9 (self-harm ideation), where a qualifier later in the
# sentence ("tapi ga sampe niat ngapa-ngapain") changes the meaning
# entirely. See docs/importantS/analisis_phq9_subgraph.md, Temuan #1.
MAX_TRAILING_WORDS_FOR_PREFIX_MATCH: int = 2


def _rule_based_score(reply: str, language: str) -> tuple[int | None, float]:
    """
    Deterministically map explicit PHQ-9 option text or a bare digit to
    a score.

    Returns
    -------
    (score, confidence):
        score       — integer 0-3, or None when no match found.
        confidence  — 1.0 for exact canonical label; 0.95 for prefix
                      match; 0.0 when unmatched.
    """
    if not reply:
        return None, 0.0

    stripped = reply.strip()

    # Bare digit: "0" / "1" / "2" / "3" (whitespace-bounded)
    m = _DIGIT_RE.match(stripped)
    if m:
        return int(m.group(1)), 1.0

    # Normalize: lowercase, strip trailing punctuation, collapse whitespace.
    normalized = _PUNCT_TAIL_RE.sub("", stripped.lower()).strip()
    normalized = _MULTI_SPACE_RE.sub(" ", normalized)

    option_map = _OPTION_MAP_ID if language.startswith("id") else _OPTION_MAP_EN

    # Exact canonical match — highest confidence.
    if normalized in option_map:
        return option_map[normalized], 1.0

    # Prefix match in both directions: user typed a leading substring of a
    # canonical label, or the canonical label is a prefix of the user reply.
    # Require at least 4 chars to avoid matching single-syllable words.
    for label, score in option_map.items():
        if len(normalized) >= 4 and label.startswith(normalized):
            return score, 0.95
        if len(label) >= 4 and normalized.startswith(label):
            remainder = normalized[len(label):].strip()
            remainder_words = remainder.split()
            if len(remainder_words) <= MAX_TRAILING_WORDS_FOR_PREFIX_MATCH:
                return score, 0.95

    return None, 0.0


def _is_direct_option_reply(reply: str, language: str) -> bool:
    """True when the user selected a PHQ-9 quick reply / canonical option.

    These inputs come from UI chips or exact option labels, so no LLM routing
    is needed. Avoiding that call keeps PHQ-9 delivery deterministic, fast, and
    cheap while preserving free-text scoring for ambiguous answers.
    """
    if not reply:
        return False
    stripped = reply.strip()
    if _DIGIT_RE.match(stripped):
        return True
    normalized = _PUNCT_TAIL_RE.sub("", stripped.lower()).strip()
    normalized = _MULTI_SPACE_RE.sub(" ", normalized)
    option_map = _OPTION_MAP_ID if language.startswith("id") else _OPTION_MAP_EN
    return normalized in option_map



# Full scoring+routing prompt — used when reply is ambiguous.
_USER_TEMPLATE = (
    "Item {item_id} of 9 (language={language}):\n"
    "\"\"\"\n{question}\n\"\"\"\n\n"
    "Options on the 0-3 scale:\n{options}\n\n"
    "Recent conversation context (last few turns):\n{context}\n\n"
    "User's latest reply:\n\"\"\"\n{reply}\n\"\"\"\n\n"
    "Respond with the JSON object only."
)

# Routing-only prompt — used when the rule-based scorer already fixed the
# score. The LLM decides action / next_item / rationale only.
_ROUTING_SYSTEM_PROMPT = (
    "You are a PHQ-9 assessment assistant. The user's score for this item "
    "has already been determined by a rule-based scorer. Your role is to:\n"
    "  1. Choose the routing action: advance, clarify, back, decline, or stop.\n"
    "  2. Set next_item (integer 1-9) if action is advance or back; otherwise null.\n"
    "  3. Write a short rationale (one sentence).\n\n"
    "Return ONLY a JSON object with exactly these keys:\n"
    '{"action": "advance|clarify|back|decline|stop", '
    '"next_item": <int|null>, '
    '"rationale": "<one sentence>"}'
)

_ROUTING_USER_TEMPLATE = (
    "Item {item_id} of 9 (language={language}):\n"
    "\"\"\"\n{question}\n\"\"\"\n\n"
    "User's latest reply:\n\"\"\"\n{reply}\n\"\"\"\n\n"
    "Rule-based scorer assigned score={score} with confidence={confidence:.2f}.\n"
    "Decide the routing action. Respond with JSON only."
)



async def judge_item_response(
    *,
    item_id: int,
    user_reply: str,
    language: str,
    recent_context: str = "",
    llm: Any | None = None,
) -> JudgeOutcome:
    """
    Hybrid judge: rule-based score + LLM routing.

    When the user's reply matches a canonical PHQ-9 option label or a
    bare digit (rule confidence >= RULE_CONFIDENCE_THRESHOLD), the score
    is fixed deterministically. The LLM is then called only for the
    routing decision (action / next_item / rationale), which keeps
    psychometric validity while still producing a natural response.

    For ambiguous replies the full LLM scoring call is used as a fallback.
    """
    client = llm if llm is not None else build_llm(PHQ9_JUDGE)

    rule_score, rule_confidence = _rule_based_score(user_reply, language)

    if rule_score is not None and rule_confidence >= RULE_CONFIDENCE_THRESHOLD:
        if _is_direct_option_reply(user_reply, language):
            return JudgeOutcome(
                score=rule_score,
                confidence=rule_confidence,
                action=JudgeAction.ADVANCE,
                next_item=None,
                rationale="direct_option_reply",
                raw="",
            )

        # Score is anchored. Ask LLM only for routing.
        routing_prompt = _ROUTING_USER_TEMPLATE.format(
            item_id=item_id,
            language=language,
            question=item_text(item_id, language),
            reply=(user_reply or "").strip(),
            score=rule_score,
            confidence=rule_confidence,
        )
        try:
            ai = await client.ainvoke(
                [
                    _SystemMessage(content=_ROUTING_SYSTEM_PROMPT),
                    _HumanMessage(content=routing_prompt),
                ]
            )
            observe_langchain_usage(ai, fallback_model=PHQ9_JUDGE.model)
            raw = ai.content if isinstance(ai.content, str) else str(ai.content)
        except Exception as exc:
            logger.warning("phq9 routing call failed: %s", exc)
            # Safe default: advance with the rule score.
            return JudgeOutcome(
                score=rule_score,
                confidence=rule_confidence,
                action=JudgeAction.ADVANCE,
                next_item=None,
                rationale="routing_error_rule_fallback",
                raw="",
            )

        outcome = _parse_routing_output(
            raw, fixed_score=rule_score, fixed_confidence=rule_confidence
        )
        if outcome.action in (JudgeAction.CLARIFY, JudgeAction.DECLINE):
            outcome = JudgeOutcome(
                score=outcome.score,
                confidence=outcome.confidence,
                action=JudgeAction.ADVANCE,
                next_item=outcome.next_item,
                rationale=f"rule_score_override:{outcome.action.value}",
                raw=outcome.raw,
            )
        logger.debug(
            "phq9 hybrid judge item=%d score=%d (rule conf=%.2f) action=%s",
            item_id, rule_score, rule_confidence, outcome.action,
        )
        return outcome

    # Ambiguous reply — fall back to full LLM scoring.
    options_block = "\n".join(
        f"  {score}. {label}" for score, label in options_with_scores(language)
    )
    user_prompt = _USER_TEMPLATE.format(
        item_id=item_id,
        language=language,
        question=item_text(item_id, language),
        options=options_block,
        context=(recent_context or "(none)").strip(),
        reply=(user_reply or "").strip(),
    )

    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=PHQ9_JUDGE.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        observe_langchain_usage(ai, fallback_model=PHQ9_JUDGE.model)
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
    except Exception as exc:
        logger.warning("phq9 judge call failed: %s", exc)
        return JudgeOutcome(
            score=0,
            confidence=0.0,
            action=JudgeAction.CLARIFY,
            next_item=None,
            rationale="judge_error",
            raw="",
        )

    logger.debug(
        "phq9 full LLM judge item=%d (rule conf=%.2f — ambiguous)",
        item_id, rule_confidence,
    )
    return _parse_judge_output(raw)



_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_routing_output(
    raw: str,
    *,
    fixed_score: int,
    fixed_confidence: float,
) -> JudgeOutcome:
    """
    Parse the routing-only LLM response and combine it with the
    deterministic rule-based score.
    """
    if not raw:
        return JudgeOutcome(
            fixed_score, fixed_confidence, JudgeAction.ADVANCE, None,
            "empty_routing_output", "",
        )

    match = _JSON_RE.search(raw)
    payload = match.group(0) if match else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("phq9 routing non-json: %r", raw[:200])
        return JudgeOutcome(
            fixed_score, fixed_confidence, JudgeAction.ADVANCE, None,
            "non_json_routing", raw,
        )

    action_raw = str(data.get("action") or "advance").strip().lower()
    try:
        action = JudgeAction(action_raw)
    except ValueError:
        action = JudgeAction.ADVANCE

    next_item = data.get("next_item")
    if not isinstance(next_item, int) or not 1 <= next_item <= 9:
        next_item = None

    rationale = str(data.get("rationale") or "").strip()[:200]

    return JudgeOutcome(
        score=fixed_score,
        confidence=fixed_confidence,
        action=action,
        next_item=next_item,
        rationale=rationale,
        raw=raw,
    )


def _parse_judge_output(raw: str) -> JudgeOutcome:
    """Parse the full LLM scoring+routing response."""
    if not raw:
        return JudgeOutcome(0, 0.0, JudgeAction.CLARIFY, None, "empty_output", "")

    match = _JSON_RE.search(raw)
    payload = match.group(0) if match else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("phq9 judge non-json: %r", raw[:200])
        return JudgeOutcome(0, 0.0, JudgeAction.CLARIFY, None, "non_json", raw)

    score = data.get("score")
    if not isinstance(score, int) or not 0 <= score <= 3:
        score = 0

    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0
    confidence = max(0.0, min(1.0, float(confidence)))

    default_action = "advance" if confidence >= RULE_CONFIDENCE_THRESHOLD else "clarify"
    action_raw = str(data.get("action") or default_action).strip().lower()
    try:
        action = JudgeAction(action_raw)
    except ValueError:
        action = JudgeAction.CLARIFY

    next_item = data.get("next_item")
    if not isinstance(next_item, int) or not 1 <= next_item <= 9:
        next_item = None

    rationale = str(data.get("rationale") or "").strip()[:200]

    return JudgeOutcome(
        score=score,
        confidence=confidence,
        action=action,
        next_item=next_item,
        rationale=rationale,
        raw=raw,
    )


__all__ = [
    "JudgeAction",
    "JudgeOutcome",
    "RULE_CONFIDENCE_THRESHOLD",
    "judge_item_response",
]

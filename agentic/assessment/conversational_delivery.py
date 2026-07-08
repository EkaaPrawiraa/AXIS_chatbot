"""init state"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from agentic.assessment.phq9 import (
    DEFAULT_LANGUAGE,
    NUM_ITEMS,
    PHQ9Severity,
    item_text,
    options_with_scores,
)
from agentic.config.llm_models import (
    PHQ9_CONVERSATION,
    PHQ9_CLARIFICATION_EXPLAINER,
    PHQ9_FEEDBACK,
    PHQ9_SCORER,
    build_llm,
)


logger = logging.getLogger(__name__)


# `msg classes`

try:  # pragma: no cover - import behavior depends on environment
    from langchain_core.messages import (  # type: ignore[import-not-found]
        HumanMessage as _HumanMessage,
        SystemMessage as _SystemMessage,
    )
except Exception:  # pragma: no cover - fallback path for tests/sandbox
    @dataclass
    class _SystemMessage:  # type: ignore[no-redef]
        content: str
        type: str = "system"

    @dataclass
    class _HumanMessage:  # type: ignore[no-redef]
        content: str
        type: str = "human"


# skor gratis


CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT: float = 0.7


@dataclass(frozen=True)
class TextScoreOutcome:
    """output: score_text_response()"""

    score: int
    confidence: float
    needs_clarification: bool
    raw_llm_text: str

    @property
    def is_auto_accepted(self) -> bool:
        return not self.needs_clarification



def build_greeting(language: str) -> str:
    """open turn 1"""
    if language == "id":
        return (
            "Aku mau ngajak kita ngecek kondisi mood-mu lewat 9 pertanyaan "
            "singkat (PHQ-9). Tiap pertanyaan menanyakan seberapa sering "
            "kamu merasakan sesuatu dalam dua minggu terakhir. Kamu bisa "
            "tap salah satu opsi atau ketik dengan kata-katamu sendiri."
        )
    return (
        "I'd like to walk through 9 short questions (PHQ-9) to check in "
        "on how you've been feeling. Each one asks how often you've "
        "felt something over the last two weeks. You can tap one of "
        "the options or just type in your own words."
    )


def build_offer(language: str) -> str:
    """start-up phrasing"""
    if language == "id":
        return (
            "Sudah beberapa minggu sejak terakhir kali kita ngecek gimana "
            "kondisimu secara keseluruhan. Mau luangin waktu sebentar "
            "buat itu sekarang, atau lebih enak ngobrol dulu?"
        )
    return (
        "It has been a few weeks since we last checked in on how you've "
        "been feeling overall. Would you like to take a few minutes for "
        "that now, or keep talking for a bit first?"
    )


def build_item_prompt(item_id: int, language: str) -> str:
    """build msg PHQ-9 item"""
    question = item_text(item_id, language)
    options = options_with_scores(language)
    if language == "id":
        header = (
            f"Pertanyaan {item_id} dari {NUM_ITEMS}. "
            f"Dalam 2 minggu terakhir, seberapa sering hal ini muncul:"
        )
        rendered = "\n".join(f"  {score}. {label}" for score, label in options)
        return f"{header}\n\n{question}\n\n{rendered}"
    header = (
        f"Question {item_id} of {NUM_ITEMS}. "
        f"Over the last 2 weeks, how often have you been bothered by:"
    )
    rendered = "\n".join(f"  {score}. {label}" for score, label in options)
    return f"{header}\n\n{question}\n\n{rendered}"


def build_clarification(item_id: int, language: str, prior_text: str) -> str:
    """cek score"""
    if language == "id":
        return (
            f"Aku ingin pastiin paham jawabanmu untuk pertanyaan {item_id}. "
            "Kalau dipikir-pikir lagi dalam dua minggu terakhir, lebih cocok "
            "yang mana: tidak sama sekali, beberapa hari, lebih dari "
            "setengah hari, atau hampir setiap hari?"
        )
    return (
        f"I want to make sure I understand your answer for question "
        f"{item_id}. Looking back over the last two weeks, which fits "
        "better: not at all, several days, more than half the days, or "
        "nearly every day?"
    )


async def build_clarification_explanation(
    *,
    item_id: int,
    language: str,
    prior_text: str,
    recent_context: str = "",
    llm: Any | None = None,
) -> str:
    """explain meaning"""
    client = llm if llm is not None else build_llm(PHQ9_CLARIFICATION_EXPLAINER)

    options_block = "\n".join(
        f"  {score}. {label}" for score, label in options_with_scores(language)
    )
    question = item_text(item_id, language)
    user_prompt = (
        f"Language: {language or DEFAULT_LANGUAGE}\n\n"
        f"Item {item_id} question:\n\"\"\"\n{question}\n\"\"\"\n\n"
        f"Answer options (0-3 scale):\n{options_block}\n\n"
        f"User asked:\n\"\"\"\n{(prior_text or '').strip()}\n\"\"\"\n\n"
        f"Recent conversation context:\n{(recent_context or '(empty)').strip()}\n"
    )

    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=PHQ9_CLARIFICATION_EXPLAINER.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
        cleaned = (raw or "").strip()
        return cleaned if cleaned else build_clarification(item_id, language, prior_text)
    except Exception as exc:
        logger.warning("phq9 clarification explanation LLM failed: %s", exc)
        return build_clarification(item_id, language, prior_text)


def build_acknowledgement(item_id: int, language: str) -> str:
    """nto the next"""
    if language == "id":
        return f"Oke, aku catat. Lanjut ke pertanyaan {item_id + 1}."
    return f"Got it, noted. Moving on to question {item_id + 1}."


# scoring llm


_SCORER_USER_TEMPLATE = (
    "PHQ-9 item {item_id} (language={language}):\n"
    '"""\n{question}\n"""\n\n'
    "Options on the 0-3 scale:\n{options}\n\n"
    'User answer:\n"""\n{answer}\n"""\n\n'
    'Respond with exactly one JSON object: '
    '{{"score": <0|1|2|3>, "confidence": <float 0..1>}}.'
)


async def score_text_response(
    *,
    item_id: int,
    user_text: str,
    language: str,
    llm: Any | None = None,
) -> TextScoreOutcome:
    """map free-text to score 0..3 LLM used at temp 0 to keep results reproducible LLM returns malformed output -> fallback to confidence 0.0 fall back to confidence 0.0 and force clarification"""
    client = llm if llm is not None else build_llm(PHQ9_SCORER)

    options_block = "\n".join(
        f"  {score}. {label}"
        for score, label in options_with_scores(language)
    )
    user_prompt = _SCORER_USER_TEMPLATE.format(
        item_id=item_id,
        language=language or DEFAULT_LANGUAGE,
        question=item_text(item_id, language),
        options=options_block,
        answer=user_text.strip(),
    )

    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=PHQ9_SCORER.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        raw = ai.content if isinstance(ai.content, str) else str(ai.content)
    except Exception as exc:
        logger.warning("phq9 scorer LLM call failed: %s", exc)
        return TextScoreOutcome(
            score=0,
            confidence=0.0,
            needs_clarification=True,
            raw_llm_text="",
        )

    score, confidence = _parse_score_json(raw)
    needs_clarification = confidence < CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT
    return TextScoreOutcome(
        score=score,
        confidence=confidence,
        needs_clarification=needs_clarification,
        raw_llm_text=raw,
    )


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_score_json(raw: str) -> tuple[int, float]:
    """const [score, confidence] = llmOutput;"""
    if not raw:
        return 0, 0.0
    match = _JSON_RE.search(raw)
    payload = match.group(0) if match else raw
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("phq9 scorer returned non-json: %r", raw)
        return 0, 0.0
    score = data.get("score")
    confidence = data.get("confidence", 0.0)
    if not isinstance(score, int) or not 0 <= score <= 3:
        return 0, 0.0
    if not isinstance(confidence, (int, float)):
        return score, 0.0
    confidence = max(0.0, min(1.0, float(confidence)))
    return int(score), confidence



_FEEDBACK_USER_TEMPLATE = (
    "PHQ-9 administration just completed.\n"
    "Language: {language}\n"
    "Total score: {total} (severity: {severity})\n"
    "Item-by-item scores: {scores}\n"
    "Item 9 was scored {item9}. "
    "{crisis_hint}"
)


async def build_feedback_message(
    *,
    total_score: int,
    severity: PHQ9Severity,
    item_scores: tuple[int, ...],
    language: str,
    item9_flagged: bool,
    llm: Any | None = None,
) -> str:
    """buat ngelipkan feedback."""
    use_llm_feedback = os.getenv("PHQ9_FEEDBACK_USE_LLM", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if llm is None and not use_llm_feedback:
        return _fallback_feedback(total_score, severity, language)

    client = llm if llm is not None else build_llm(PHQ9_FEEDBACK)
    crisis_hint = (
        "Item 9 was non-zero so the response should gently note that "
        "we will take a closer look at safety right after this message."
        if item9_flagged
        else "Item 9 was zero so no safety routing is needed."
    )
    user_prompt = _FEEDBACK_USER_TEMPLATE.format(
        language=language,
        total=total_score,
        severity=severity.value,
        scores=", ".join(str(s) for s in item_scores),
        item9=item_scores[-1],
        crisis_hint=crisis_hint,
    )
    try:
        ai = await client.ainvoke(
            [
                _SystemMessage(content=PHQ9_FEEDBACK.system_prompt),
                _HumanMessage(content=user_prompt),
            ]
        )
        text = ai.content if isinstance(ai.content, str) else str(ai.content)
        return text.strip()
    except Exception as exc:
        logger.warning("phq9 feedback LLM call failed: %s", exc)
        return _fallback_feedback(total_score, severity, language)


def _fallback_feedback(
    total: int, severity: PHQ9Severity, language: str
) -> str:
    """`use static feedback`"""
    if language == "id":
        severity_label = {
            "minimal": "minimal",
            "mild": "ringan",
            "moderate": "sedang",
            "moderately_severe": "cukup tinggi",
            "severe": "tinggi",
        }.get(severity.value, severity.value)
        return (
            f"Skor PHQ-9 kamu adalah {total}. Ini berada pada rentang "
            f"{severity_label} dalam skrining PHQ-9, bukan diagnosis. "
            "Terima kasih sudah meluangkan waktu menjawab. Kalau terasa "
            "berat atau berlanjut, kamu bisa mempertimbangkan ngobrol "
            "dengan profesional atau layanan konseling kampus. Kita juga "
            "bisa lanjut ngobrol pelan-pelan di sini."
        )
    return (
        f"Your PHQ-9 score is {total}. This falls in the {severity.value} "
        "range for PHQ-9 screening, not a diagnosis. Thank you for taking "
        "the time to answer. If this feels heavy or keeps going, you could "
        "consider talking with a trained professional or campus counseling "
        "support. We can also keep talking from here at your pace."
    )


__all__ = [
    "TextScoreOutcome",
    "CONFIDENCE_FLOOR_FOR_AUTO_ACCEPT",
    "build_greeting",
    "build_offer",
    "build_item_prompt",
    "build_clarification",
    "build_acknowledgement",
    "score_text_response",
    "build_feedback_message",
]

"""Rule-based scoring and filtering utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from utility.languange.language_filtering_LLM.lexicons import (
    MENTAL_HEALTH_SEEDS,
    MENTAL_PATTERNS,
    SLANG_MARKERS,
    SLANG_PATTERNS,
    STOPWORDS,
)


@dataclass(frozen=True)
class ScoreBreakdown:
    slang_score: float
    mental_score: float
    language_score: float
    total: float


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def is_stopword(term: str) -> bool:
    return _normalize(term) in STOPWORDS


def score_slang(term: str, examples: Iterable[str]) -> float:
    term_norm = _normalize(term)
    score = 0.0
    if term_norm in SLANG_MARKERS:
        score += 1.0
    for pat in SLANG_PATTERNS:
        if re.search(pat, term_norm):
            score += 0.6
    for ex in examples:
        ex_norm = _normalize(ex)
        if any(m in ex_norm for m in SLANG_MARKERS):
            score += 0.3
    return score


def score_mental(term: str, definition: str, examples: Iterable[str]) -> float:
    term_norm = _normalize(term)
    score = 0.0
    if term_norm in MENTAL_HEALTH_SEEDS:
        score += 1.5
    if any(seed in term_norm for seed in MENTAL_HEALTH_SEEDS):
        score += 0.5
    combined = " ".join([definition] + list(examples))
    combined = _normalize(combined)
    for pat in MENTAL_PATTERNS:
        if re.search(pat, combined):
            score += 0.8
    return score


def score_language(term: str) -> float:
    # Simple heuristic: ASCII letters only indicates Indo/English.
    if re.fullmatch(r"[a-zA-Z\s\-']+", term):
        return 0.5
    return 0.0


def compute_score(term: str, definition: str, examples: Iterable[str]) -> ScoreBreakdown:
    slang_score = score_slang(term, examples)
    mental_score = score_mental(term, definition, examples)
    language_score = score_language(term)
    total = slang_score + mental_score + language_score
    return ScoreBreakdown(
        slang_score=slang_score,
        mental_score=mental_score,
        language_score=language_score,
        total=total,
    )

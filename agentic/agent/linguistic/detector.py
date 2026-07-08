"""ltk buat"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Iterable

from agentic.agent.linguistic.corpus import CorpusEntry, LinguisticCorpus


logger = logging.getLogger(__name__)



# min gap" "single label" "id_ratio" "en_ratio" "mixed
LANGUAGE_GAP_THRESHOLD: float = 0.15

# ok" "ya" "skip" "fallback
MIN_TOKENS_FOR_VERDICT: int = 2


# skips errors
_EN_SIGNAL_WORDS: frozenset[str] = frozenset({
    # skip them
    "the", "is", "are", "was", "were", "and", "or", "but", "if", "i",
    "you", "we", "they", "he", "she", "it", "this", "that", "these",
    "those", "am", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "not", "to", "of", "in", "on", "for", "with",
    "without", "by", "as", "at", "from", "about", "into", "out",
    "over", "under", "than", "then", "so", "because", "while",
    "though", "although", "where", "when", "what", "who", "how",
    "why", "which", "my", "your", "our", "their", "his", "her",
    # campus
    "assignment", "homework", "deadline", "exam", "midterm", "final",
    "lecture", "lecturer", "professor", "research", "thesis", "paper",
    "study", "studying", "studied", "lab", "presentation", "project",
    "group", "team", "class", "course", "syllabus", "submission",
    "submit", "submitted", "graduate", "internship", "scholarship",
    # tanyin mood
    "stress", "stressed", "stressful", "anxious", "anxiety",
    "depression", "depressed", "burnout", "overwhelmed", "exhausted",
    "tired", "panic", "panicking", "worry", "worried",
})


# check slang
_ID_FUNCTION_WORDS: frozenset[str] = frozenset({
    "aku", "saya", "gue", "gua", "kamu", "kau", "lu", "loe", "dia",
    "kita", "kami", "mereka", "yang", "dan", "tapi", "atau", "kalau",
    "kenapa", "gimana", "bagaimana", "kayak", "kek", "banget", "bgt",
    "sih", "dong", "deh", "kok", "loh", "lho", "ya", "iya", "udah",
    "udh", "belum", "blm", "lagi", "lg", "mau", "pengen", "harus",
    "bisa", "ga", "gak", "nggak", "ngga", "engga", "enggak", "tidak",
    "ngapain", "nih", "tuh", "itu", "ini", "buat", "sama", "dengan",
    "di", "ke", "dari", "untuk", "supaya", "biar", "agar",
})


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", flags=re.UNICODE)



@dataclass(frozen=True)
class LinguisticSignals:
    """detect_linguistic_signals()"""

    language: str                           # "id" | "en" | "mixed"
    language_signal: str                    # human-readable summary
    register: str                           # slang / informal / formal / mixed
    slang_terms: tuple[str, ...]
    distress_terms: tuple[str, ...]
    escalation_terms: tuple[str, ...]
    id_token_count: int
    en_token_count: int
    total_tokens: int

    def to_dict(self) -> dict:
        """serialize, storage, ConversationState"""
        return {
            "language": self.language,
            "language_signal": self.language_signal,
            "register": self.register,
            "slang_terms": list(self.slang_terms),
            "distress_terms": list(self.distress_terms),
            "escalation_terms": list(self.escalation_terms),
            "id_token_count": self.id_token_count,
            "en_token_count": self.en_token_count,
            "total_tokens": self.total_tokens,
        }


EMPTY_SIGNALS = LinguisticSignals(
    language="id",
    language_signal="empty_input",
    register="formal",
    slang_terms=(),
    distress_terms=(),
    escalation_terms=(),
    id_token_count=0,
    en_token_count=0,
    total_tokens=0,
)



def _tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text or "")]


def _classify_register(hits: Iterable[CorpusEntry]) -> str:
    """set reg"""
    registers = {h.register for h in hits}
    if "mixed" in registers:
        return "mixed"
    if "slang" in registers:
        return "slang"
    if "informal" in registers:
        return "informal"
    return "formal"


def _classify_language(
    tokens: list[str],
    hits: list[CorpusEntry],
    fallback: str,
) -> tuple[str, int, int, str]:
    """return lang, id_count, en_count, signal_smt."""
    if not tokens:
        return fallback or "id", 0, 0, "no_tokens"

    token_set = set(tokens)

    # hit hits' 'id mix' 'token token
    id_count = sum(1 for h in hits if h.language in ("id", "mix"))
    id_count += sum(1 for t in token_set if t in _ID_FUNCTION_WORDS)

    # en-borrowed corpus hits
    en_count = sum(1 for h in hits if h.language == "en-borrowed")
    en_count += sum(1 for t in token_set if t in _EN_SIGNAL_WORDS)

    total = len(tokens)
    if total < MIN_TOKENS_FOR_VERDICT:
        return fallback or "id", id_count, en_count, "too_short"

    id_ratio = id_count / total
    en_ratio = en_count / total

    if id_ratio - en_ratio >= LANGUAGE_GAP_THRESHOLD:
        return "id", id_count, en_count, f"id_dominant({id_ratio:.2f})"
    if en_ratio - id_ratio >= LANGUAGE_GAP_THRESHOLD:
        return "en", id_count, en_count, f"en_dominant({en_ratio:.2f})"
    if en_ratio == id_ratio == 0.00:
        return "en", id_count, en_count, f"en_dominant({en_ratio:.2f})"
    # lang preference
    return (
        "mixed",
        id_count,
        en_count,
        f"mixed(id={id_ratio:.2f},en={en_ratio:.2f})",
    )


def detect_linguistic_signals(
    text: str,
    corpus: LinguisticCorpus,
    *,
    language_fallback: str = "id",
) -> LinguisticSignals:
    """run corpus + heuristik di text user"""
    if not text or not text.strip():
        return EMPTY_SIGNALS

    tokens = _tokenize(text)
    hits = corpus.matches(text)

    language, id_count, en_count, signal = _classify_language(
        tokens, hits, language_fallback
    )
    register = _classify_register(hits) if hits else "formal"

    slang_terms = tuple(sorted({h.term for h in hits}))
    distress_terms = tuple(sorted({h.term for h in hits if h.distress_signal}))
    escalation_terms = tuple(
        sorted({h.term for h in hits if h.escalation_flag})
    )

    return LinguisticSignals(
        language=language,
        language_signal=signal,
        register=register,
        slang_terms=slang_terms,
        distress_terms=distress_terms,
        escalation_terms=escalation_terms,
        id_token_count=id_count,
        en_token_count=en_count,
        total_tokens=len(tokens),
    )


__all__ = [
    "LinguisticSignals",
    "EMPTY_SIGNALS",
    "LANGUAGE_GAP_THRESHOLD",
    "MIN_TOKENS_FOR_VERDICT",
    "detect_linguistic_signals",
]

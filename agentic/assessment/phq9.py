"""scoring core PHQ-9"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Mapping, Sequence



ITEMS_ID: tuple[str, ...] = (
    "Sedikit minat atau kesenangan dalam melakukan aktivitas.",
    "Merasa sedih, tertekan, atau putus asa.",
    "Sulit tidur, mudah terbangun, atau tidur terlalu banyak.",
    "Merasa lelah atau kurang tenaga.",
    "Selera makan buruk atau makan berlebihan.",
    "Merasa buruk tentang diri sendiri, gagal, atau mengecewakan keluarga.",
    "Sulit berkonsentrasi pada hal seperti membaca atau menonton.",
    "Bergerak atau berbicara terlalu lambat sehingga orang lain memperhatikan, "
    "atau sebaliknya, sangat gelisah sampai bergerak lebih banyak dari biasanya.",
    "Berpikir lebih baik mati atau ingin menyakiti diri sendiri.",
)


ITEMS_EN: tuple[str, ...] = (
    "Little interest or pleasure in doing things.",
    "Feeling down, depressed, or hopeless.",
    "Trouble falling or staying asleep, or sleeping too much.",
    "Feeling tired or having little energy.",
    "Poor appetite or overeating.",
    "Feeling bad about yourself, or that you are a failure, or that "
    "you have let yourself or your family down.",
    "Trouble concentrating on things, such as reading the newspaper "
    "or watching television.",
    "Moving or speaking so slowly that other people could have noticed, "
    "or the opposite, being so fidgety or restless that you have been "
    "moving a lot more than usual.",
    "Thoughts that you would be better off dead, or thoughts of "
    "hurting yourself in some way.",
)


OPTION_LABELS_ID: tuple[str, ...] = (
    "Tidak sama sekali",
    "Beberapa hari",
    "Lebih dari setengah hari",
    "Hampir setiap hari",
)


OPTION_LABELS_EN: tuple[str, ...] = (
    "Not at all",
    "Several days",
    "More than half the days",
    "Nearly every day",
)


# skp klo error
NUM_ITEMS: int = 9
ITEM9_INDEX_ZERO_BASED: int = 8
ITEM9_INDEX_ONE_BASED: int = 9



class PHQ9Severity(str, Enum):
    """set bands"""

    MINIMAL = "minimal"
    MILD = "mild"
    MODERATE = "moderate"
    MODERATELY_SEVERE = "moderately_severe"
    SEVERE = "severe"


_SEVERITY_BANDS: tuple[tuple[int, int, PHQ9Severity], ...] = (
    (0, 4, PHQ9Severity.MINIMAL),
    (5, 9, PHQ9Severity.MILD),
    (10, 14, PHQ9Severity.MODERATE),
    (15, 19, PHQ9Severity.MODERATELY_SEVERE),
    (20, 27, PHQ9Severity.SEVERE),
)


def compute_severity(total: int) -> PHQ9Severity:
    """map 0..27 to severity band"""
    if not 0 <= total <= 27:
        raise ValueError(f"PHQ-9 total must be in [0, 27], got {total}")
    for low, high, band in _SEVERITY_BANDS:
        if low <= total <= high:
            return band
    raise AssertionError("severity band lookup must cover 0..27 fully")



class ResponseSource(str, Enum):
    """answ"""

    BUTTON = "button"
    TEXT_LLM = "text_llm"
    RETRY_BUTTON = "retry_button"


@dataclass(frozen=True)
class PHQ9Response:
    """res[0]"""

    item_id: int  # 1-based
    score: int
    source: ResponseSource
    raw_text: str | None = None
    confidence: float | None = None  # only meaningful for TEXT_LLM

    def __post_init__(self) -> None:
        if not 1 <= self.item_id <= NUM_ITEMS:
            raise ValueError(
                f"item_id must be in [1, {NUM_ITEMS}], got {self.item_id}"
            )
        if not 0 <= self.score <= 3:
            raise ValueError(f"score must be in [0, 3], got {self.score}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0.0, 1.0]")


@dataclass(frozen=True)
class PHQ9Result:
    """buat admin"""

    user_id: str
    session_id: str
    total_score: int
    severity: PHQ9Severity
    item_scores: tuple[int, ...]  # length NUM_ITEMS, 0-based order
    item9_score: int
    delta_from_previous: int | None  # positive = worsening
    administered_at: datetime
    language: str
    sources: tuple[ResponseSource, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if len(self.item_scores) != NUM_ITEMS:
            raise ValueError(
                f"item_scores must have {NUM_ITEMS} entries, "
                f"got {len(self.item_scores)}"
            )
        if any(not 0 <= s <= 3 for s in self.item_scores):
            raise ValueError("each item_scores entry must be in [0, 3]")
        if self.item9_score != self.item_scores[ITEM9_INDEX_ZERO_BASED]:
            raise ValueError("item9_score must match item_scores[8]")

    @property
    def item9_flagged(self) -> bool:
        """score != 0"""
        return self.item9_score >= 1



def score_phq9(
    *,
    user_id: str,
    session_id: str,
    responses: Iterable[PHQ9Response],
    language: str,
    previous_total: int | None = None,
    administered_at: datetime | None = None,
) -> PHQ9Result:
    """aggregate responses"""
    by_item: dict[int, PHQ9Response] = {}
    for r in responses:
        if r.item_id in by_item:
            raise ValueError(f"duplicate response for item {r.item_id}")
        by_item[r.item_id] = r

    missing = [i for i in range(1, NUM_ITEMS + 1) if i not in by_item]
    if missing:
        raise ValueError(f"missing PHQ-9 responses for items: {missing}")

    item_scores = tuple(by_item[i].score for i in range(1, NUM_ITEMS + 1))
    sources = tuple(by_item[i].source for i in range(1, NUM_ITEMS + 1))
    total = sum(item_scores)
    severity = compute_severity(total)
    delta = (total - previous_total) if previous_total is not None else None

    return PHQ9Result(
        user_id=user_id,
        session_id=session_id,
        total_score=total,
        severity=severity,
        item_scores=item_scores,
        item9_score=item_scores[ITEM9_INDEX_ZERO_BASED],
        delta_from_previous=delta,
        administered_at=administered_at or datetime.now(timezone.utc),
        language=language,
        sources=sources,
    )



SUPPORTED_LANGUAGES: tuple[str, ...] = ("id", "en")
DEFAULT_LANGUAGE: str = "id"


def get_items(language: str) -> tuple[str, ...]:
    """ret prompts 9"""
    return ITEMS_ID if _normalize_lang(language) == "id" else ITEMS_EN


def get_option_labels(language: str) -> tuple[str, ...]:
    """ret four lbls 0..3"""
    return (
        OPTION_LABELS_ID
        if _normalize_lang(language) == "id"
        else OPTION_LABELS_EN
    )


def _normalize_lang(language: str) -> str:
    code = (language or DEFAULT_LANGUAGE).strip().lower()
    if code.startswith("id"):
        return "id"
    if code.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE



_ID_HINT_TOKENS: frozenset[str] = frozenset(
    {
        "saya", "aku", "tidak", "yang", "dan", "atau", "kamu", "dia",
        "merasa", "ingin", "kerja", "tidur", "lelah", "sedih", "minggu",
        "hari", "bulan", "sekarang", "kemarin", "besok", "banget",
        "kenapa", "bagaimana", "apakah", "udah", "belum", "masih",
        "rumah", "teman", "keluarga", "orangtua", "kuliah", "sekolah",
    }
)


def detect_language_lightweight(text: str) -> str:
    """en" or "id"""
    if not text or not text.strip():
        return DEFAULT_LANGUAGE
    tokens = set(re.findall(r"[a-zA-ZÀ-ÿ]+", text.lower()))
    return "id" if tokens & _ID_HINT_TOKENS else "en"


def resolve_language(
    *,
    user_pref: str | None,
    recent_messages: Sequence[str] | None = None,
) -> str:
    """`set lang`"""
    if user_pref:
        normalized = _normalize_lang(user_pref)
        if normalized in SUPPORTED_LANGUAGES:
            return normalized
    if recent_messages:
        for msg in reversed(recent_messages):
            if msg and msg.strip():
                return detect_language_lightweight(msg)
    return DEFAULT_LANGUAGE



def item_text(item_id: int, language: str) -> str:
    """ret prompt 1"""
    if not 1 <= item_id <= NUM_ITEMS:
        raise ValueError(f"item_id must be in [1, {NUM_ITEMS}]")
    return get_items(language)[item_id - 1]


def options_with_scores(language: str) -> tuple[tuple[int, str], ...]:
    """return ((0, label0), (1, label1), ...)"""
    labels = get_option_labels(language)
    return tuple((i, labels[i]) for i in range(4))


def to_storage_payload(result: PHQ9Result) -> Mapping[str, object]:
    """serialize PHQ9Result to assessments table"""
    return {
        "user_id": result.user_id,
        "session_id": result.session_id,
        "instrument": "PHQ-9",
        "score": float(result.total_score),
        "severity_label": result.severity.value,
        "item_responses": {
            str(i + 1): result.item_scores[i] for i in range(NUM_ITEMS)
        },
        "delta_from_prev": (
            float(result.delta_from_previous)
            if result.delta_from_previous is not None
            else None
        ),
        "administered_at": result.administered_at.isoformat(),
        "administered_by": "chatbot",
    }


__all__ = [
    "ITEMS_ID",
    "ITEMS_EN",
    "OPTION_LABELS_ID",
    "OPTION_LABELS_EN",
    "NUM_ITEMS",
    "ITEM9_INDEX_ZERO_BASED",
    "ITEM9_INDEX_ONE_BASED",
    "PHQ9Severity",
    "ResponseSource",
    "PHQ9Response",
    "PHQ9Result",
    "score_phq9",
    "compute_severity",
    "get_items",
    "get_option_labels",
    "detect_language_lightweight",
    "resolve_language",
    "item_text",
    "options_with_scores",
    "to_storage_payload",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]

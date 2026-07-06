"""Corpus loader for the Indonesian slang / clinical lexicon."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


logger = logging.getLogger(__name__)



_DEFAULT_CORPUS_PATH = (
    Path(__file__).resolve().parents[3]
    / "utility"
    / "languange"
    / "data_ready_to_fed"
    / "linguistic_ready.jsonl"
)



@dataclass(frozen=True)
class CorpusEntry:
    """One canonical entry from the linguistic lexicon."""

    term: str                       # lowercased surface form
    category: str                   # "L1" | "L2" | "L3"
    language: str                   # "id" | "en-borrowed" | "mix"
    register: str                   # "slang" | "informal" | "formal" | "mixed"
    emotional_weight: str           # "low" | "medium" | "high"
    distress_signal: bool
    escalation_flag: bool

    @property
    def is_id_native(self) -> bool:
        return self.language == "id"

    @property
    def is_loanword(self) -> bool:
        return self.language == "en-borrowed"


def _coerce_entry(raw: dict) -> CorpusEntry | None:
    """Best-effort coercion of one JSONL row into a CorpusEntry."""
    term = raw.get("term")
    if not isinstance(term, str) or not term.strip():
        return None
    return CorpusEntry(
        term=term.strip().lower(),
        category=str(raw.get("category") or "L1"),
        language=str(raw.get("language") or "id"),
        register=str(raw.get("register") or "slang"),
        emotional_weight=str(raw.get("emotional_weight") or "low"),
        distress_signal=bool(raw.get("distress_signal", False)),
        escalation_flag=bool(raw.get("escalation_flag", False)),
    )



@dataclass
class LinguisticCorpus:
    """
    Indexed slang / clinical lexicon optimized for substring matching.

    Two indices are maintained:

    *   ``_single_word``: words that are exactly one token. Matched via
        a single compiled regex with word boundaries so we do not
        false-positive on substrings (e.g. "tugas" inside "petugas").
    *   ``_multi_word``: phrases of 2+ tokens. Matched via direct
        ``in`` check on the lowered message because regex with many
        alternations gets expensive.
    """

    entries: tuple[CorpusEntry, ...] = field(default_factory=tuple)
    _single_word: dict[str, CorpusEntry] = field(default_factory=dict, repr=False)
    _multi_word: tuple[CorpusEntry, ...] = field(default_factory=tuple, repr=False)
    _single_pattern: re.Pattern[str] | None = field(default=None, repr=False)

    @classmethod
    def from_entries(cls, entries: Iterable[CorpusEntry]) -> "LinguisticCorpus":
        seen: dict[str, CorpusEntry] = {}
        for e in entries:
            # Last writer wins on duplicate terms.
            seen[e.term] = e
        all_entries = tuple(seen.values())

        single: dict[str, CorpusEntry] = {}
        multi: list[CorpusEntry] = []
        for entry in all_entries:
            tokens = entry.term.split()
            if len(tokens) == 1:
                single[entry.term] = entry
            else:
                multi.append(entry)

        pattern: re.Pattern[str] | None = None
        if single:
            alt = "|".join(sorted(map(re.escape, single.keys()), key=len, reverse=True))
            pattern = re.compile(rf"\b({alt})\b", flags=re.IGNORECASE)

        return cls(
            entries=all_entries,
            _single_word=single,
            _multi_word=tuple(multi),
            _single_pattern=pattern,
        )

    # lookups.

    def matches(self, text: str) -> list[CorpusEntry]:
        """Return all corpus entries that appear in ``text``."""
        if not text:
            return []
        lowered = text.lower()

        hits: list[CorpusEntry] = []
        if self._single_pattern is not None:
            for match in self._single_pattern.finditer(lowered):
                term = match.group(1).lower()
                entry = self._single_word.get(term)
                if entry is not None:
                    hits.append(entry)

        for entry in self._multi_word:
            if entry.term in lowered:
                hits.append(entry)

        return hits

    def __len__(self) -> int:
        return len(self.entries)



_corpus_cache: dict[str, LinguisticCorpus] = {}


def load_corpus(path: Path) -> LinguisticCorpus:
    """Load and cache a corpus from a JSONL file."""
    abs_path = str(path.resolve())
    cached = _corpus_cache.get(abs_path)
    if cached is not None:
        return cached

    entries: list[CorpusEntry] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "linguistic corpus line %d invalid json: %s",
                        line_no,
                        exc,
                    )
                    continue
                entry = _coerce_entry(raw)
                if entry is not None:
                    entries.append(entry)
    except FileNotFoundError:
        logger.warning("linguistic corpus not found at %s; using empty", path)

    corpus = LinguisticCorpus.from_entries(entries)
    _corpus_cache[abs_path] = corpus
    logger.info(
        "linguistic corpus loaded: %d entries from %s",
        len(corpus),
        abs_path,
    )
    return corpus


def load_default_corpus() -> LinguisticCorpus:
    """Load the shipped slang / clinical lexicon."""
    return load_corpus(_DEFAULT_CORPUS_PATH)


def clear_cache() -> None:
    """Used by tests that load fixture corpora."""
    _corpus_cache.clear()


__all__ = [
    "CorpusEntry",
    "LinguisticCorpus",
    "load_corpus",
    "load_default_corpus",
    "clear_cache",
]

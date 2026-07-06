"""Configuration for slang/mental-health filtering pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out"

RAW_DIR = (
    Path(__file__).resolve().parent.parent
    / "language_scrapping"
    / "data"
    / "raw"
)


@dataclass(frozen=True)
class FilterConfig:
    min_term_len: int = 2
    max_term_len: int = 40
    max_usage_examples: int = 3
    min_score_keep: float = 1.0
    max_keep: int = 100000000
    include_english: bool = True
    include_indonesian: bool = True


DEFAULT_CONFIG = FilterConfig()

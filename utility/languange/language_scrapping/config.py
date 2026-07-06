"""Configuration for the Indonesian linguistic context pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SOURCES_DIR = DATA_DIR / "sources"
RAW_DIR = DATA_DIR / "raw"
OUT_DIR = BASE_DIR / "out"


@dataclass(frozen=True)
class PipelineConfig:
    max_prompt_tokens: int = 600
    token_estimate_ratio: float = 1.3
    max_prompt_entries: int = 120


DEFAULT_CONFIG = PipelineConfig()

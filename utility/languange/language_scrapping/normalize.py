"""Normalization helpers for terms and text fields."""

from __future__ import annotations

import re


_WS_RE = re.compile(r"\s+")


def normalize_term(term: str) -> str:
    if not term:
        return ""
    cleaned = term.strip().lower()
    cleaned = _WS_RE.sub(" ", cleaned)
    return cleaned


def normalize_text(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = _WS_RE.sub(" ", cleaned)
    return cleaned

"""set to C."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Candidate:
    id: str
    type: str
    text: str
    source_signal: str
    similarity: float = 0.0
    importance: float = 0.0
    created_at_iso: str | None = None
    relation_richness: float = 0.0
    safety_relevance: float = 0.0
    hydrated: dict[str, Any] | None = None

    # skip error
    rank_in_signal: int = 0
    rrf_score: float = 0.0
    final_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "source_signal": self.source_signal,
            "similarity": self.similarity,
            "importance": self.importance,
            "relation_richness": self.relation_richness,
            "safety_relevance": self.safety_relevance,
            "rrf_score": self.rrf_score,
            "final_score": self.final_score,
            "hydrated": self.hydrated,
        }



_RECENCY_HALF_LIFE_DAYS: float = 30.0


def _recency_score(created_at_iso: str | None) -> float:
    """score = exp(-ln2 * days / half_life)"""
    if not created_at_iso:
        return 0.5
    try:
        if isinstance(created_at_iso, str):
            dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
        else:
            return 0.5
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = max((now - dt).total_seconds() / 86400.0, 0.0)
        return math.exp(-math.log(2) * days / _RECENCY_HALF_LIFE_DAYS)
    except Exception:
        return 0.5


def compute_relation_richness(hydrated: dict[str, Any] | None) -> float:
    """return score kg dims"""
    if not hydrated:
        return 0.0
    score = 0.0
    if hydrated.get("subjects") or hydrated.get("subject"):
        score += 0.20
    if hydrated.get("triggers"):
        score += 0.20
    if hydrated.get("emotions"):
        score += 0.20
    if hydrated.get("thoughts"):
        score += 0.20
    if hydrated.get("behaviors"):
        score += 0.20
    return score


def candidate_recency_score(c: Candidate) -> float:
    """buat scoring"""
    return _recency_score(c.created_at_iso)

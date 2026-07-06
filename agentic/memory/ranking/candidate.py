"""Candidate dataclass — unified representation across all retrieval signals.

Every signal (pgvector Memory, pgvector Experience, KG traversal, keyword
fallback) normalises its output into a Candidate so the three-stage ranking
pipeline (RRF → graph reranker → MMR) can operate on a single type.

Field semantics
---------------
id              : Neo4j node id (or synthetic key for nodes without one)
type            : "Memory" | "Experience" | "Subject" | "Theme" | "Trigger"
text            : human-readable summary / description used for MMR similarity
source_signal   : which retrieval signal produced this candidate
similarity      : cosine similarity from pgvector (0.0 if unavailable)
importance      : Memory.importance or Experience.significance (0.0 if N/A)
created_at_iso  : ISO-8601 string for recency score computation (None ok)
relation_richness : 0–1 score computed by compute_relation_richness()
safety_relevance  : 0–1 signal for crisis / safety-flagged content
hydrated        : full KG neighbourhood dict returned by _rehydrate_*()

rank_in_signal and rrf_score are set by rrf_fuse(); final_score by
graph_rerank(). They start at 0 and are filled in during the pipeline.
"""

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

    # set by pipeline stages
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
    """Exponential decay: score = exp(-ln2 * days / half_life).

    Returns 0.5 (neutral) when the timestamp is unavailable so the
    recency component does not break the overall formula.

    Exponential decay is the standard approach for time-discounted
    retrieval — see Manning, Raghavan & Schütze (2008), Section 7.1.
    """
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
    """Return 0–1 score based on how many KG dimensions are populated.

    The five cognitive-chain dimensions (subject, trigger, emotion, thought,
    behavior) each contribute 0.20. A candidate with a full
    Experience → Trigger → Emotion → Thought → Behavior chain gets 1.0.

    This operationalises the claim that KG retrieval should be credited for
    causal structure beyond what a flat vector store provides, consistent
    with the graph-enhanced RAG framing in Edge et al. (2024).
    """
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
    """Compute recency score for a Candidate using its created_at_iso."""
    return _recency_score(c.created_at_iso)

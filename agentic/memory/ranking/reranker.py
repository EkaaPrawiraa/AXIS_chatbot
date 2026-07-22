"""skip error"""

from __future__ import annotations

from typing import Any

from agentic.memory.ranking.candidate import Candidate, candidate_recency_score

# skip klo error
_W_RRF   = 0.50
_W_IMP   = 0.15
_W_RICH  = 0.15
_W_REC   = 0.10
_W_SAFE  = 0.10

# mmr_default_lambda
MMR_LAMBDA: float = 0.70


def graph_rerank(
    candidates: list[Candidate],
    rrf_scores: dict[str, float],
    *,
    w_rrf:  float = _W_RRF,
    w_imp:  float = _W_IMP,
    w_rich: float = _W_RICH,
    w_rec:  float = _W_REC,
    w_safe: float = _W_SAFE,
) -> list[Candidate]:
    """srt_by_fin_score"""
    max_rrf = max(rrf_scores.values(), default=1.0)
    if max_rrf == 0.0:
        max_rrf = 1.0

    for c in candidates:
        c.rrf_score = rrf_scores.get(c.id, 0.0)
        normalised_rrf = c.rrf_score / max_rrf
        recency = candidate_recency_score(c)
        c.final_score = (
            w_rrf  * normalised_rrf
            + w_imp  * min(c.importance, 1.0)
            + w_rich * c.relation_richness
            + w_rec  * recency
            + w_safe * c.safety_relevance
        )

    candidates.sort(key=lambda c: c.final_score, reverse=True)
    return candidates


def _jaccard(text_a: str, text_b: str) -> float:
    """token-level jaccard"""
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def mmr_select(
    ranked_candidates: list[Candidate],
    *,
    top_n: int = 8,
    lambda_: float = MMR_LAMBDA,
) -> list[Candidate]:
    """ngambil top_n"""
    selected: list[Candidate] = []
    remaining = list(ranked_candidates)

    while remaining and len(selected) < top_n:
        best: Candidate | None = None
        best_score: float = float("-inf")

        for c in remaining:
            relevance = c.final_score
            if not selected:
                mmr_score = relevance
            else:
                max_sim = max(_jaccard(c.text, s.text) for s in selected)
                mmr_score = lambda_ * relevance - (1.0 - lambda_) * max_sim

            if mmr_score > best_score:
                best_score = mmr_score
                best = c

        if best is None:
            break
        selected.append(best)
        remaining.remove(best)

    return selected

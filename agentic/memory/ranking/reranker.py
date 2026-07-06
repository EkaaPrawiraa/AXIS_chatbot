"""Graph reranker and MMR deduplication.

Graph Reranker
--------------
After RRF fusion, candidates are boosted by four metadata signals drawn
from the Neo4j knowledge graph:

    final_score =
        w_rrf  * normalised_rrf
      + w_imp  * importance_or_significance
      + w_rich * relation_richness
      + w_rec  * recency_score
      + w_safe * safety_relevance

Default weights (from design doc kg_context_structuring_and_ranking_strategy):
  w_rrf  = 0.50   (primary: favours candidates consistently ranked across signals)
  w_imp  = 0.15   (Memory.importance or Experience.significance)
  w_rich = 0.15   (fraction of KG chain dimensions populated)
  w_rec  = 0.10   (exponential decay with 30-day half-life)
  w_safe = 0.10   (crisis / safety-flagged content boost)

The weighting scheme is consistent with the hybrid scoring literature
reviewed in Robertson & Zaragoza (2009) and the graph-enhanced RAG design
in Edge et al. (2024).

Maximal Marginal Relevance (MMR)
---------------------------------
MMR selects the next candidate by maximising:

    MMR(d) = λ · relevance(query, d) − (1 − λ) · max_sim(d, selected)

where max_sim is the maximum lexical Jaccard similarity between d and any
already-selected candidate.  This avoids repeating the same fact across
multiple prompt bullets.

Reference
---------
Carbonell, J., & Goldstein, J. (1998).
  "The use of MMR, diversity-based reranking for reordering documents and
  producing summaries."
  In Proceedings of the 21st Annual International ACM SIGIR Conference on
  Research and Development in Information Retrieval (SIGIR '98), pp. 335–336.
  https://doi.org/10.1145/290941.291025

λ = 0.70 emphasises relevance over diversity, appropriate for a
therapeutic companion where staying on topic matters more than breadth.
"""

from __future__ import annotations

from typing import Any

from agentic.memory.ranking.candidate import Candidate, candidate_recency_score

# Graph reranker default weights
_W_RRF   = 0.50
_W_IMP   = 0.15
_W_RICH  = 0.15
_W_REC   = 0.10
_W_SAFE  = 0.10

# MMR default lambda
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
    """Apply weighted graph reranking on top of RRF scores.

    Mutates each Candidate's `rrf_score` and `final_score` in-place.
    Returns the list sorted by `final_score` descending.
    """
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
    """Token-level Jaccard similarity for lexical deduplication.

    Note: Jaccard is appropriate here because we are comparing full candidate
    summaries of similar length to detect semantic overlap, not matching a
    short phrase against a long utterance (where Dice is preferred for its
    asymmetry handling).  See Kondrak (2005) for a comparison of similarity
    measures in NLP contexts.
    """
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
    """Select up to `top_n` candidates via MMR (Carbonell & Goldstein 1998).

    `ranked_candidates` must already be sorted by `final_score` descending
    (i.e. graph_rerank() must have been called first).

    The greedy MMR selection picks the candidate maximising:
        λ · relevance − (1 − λ) · max_sim(c, already_selected)
    where relevance = c.final_score and max_sim uses lexical Jaccard on
    candidate texts.  The greedy approximation is O(n²) in the number of
    candidates, but n ≤ FOCUSED_TOP_K (typically 5–8) so it is negligible.
    """
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

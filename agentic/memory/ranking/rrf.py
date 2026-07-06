"""Reciprocal Rank Fusion (RRF) for heterogeneous retrieval signals.

RRF fuses multiple ranked lists without assuming that scores from different
signals are on the same scale.  A document ranked r in list i contributes
1/(k + r) to its total RRF score.  Documents appearing in many lists — or
near the top of several lists — accumulate high scores.

Reference
---------
Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009).
  "Reciprocal rank fusion outperforms Condorcet and individual rank
  learning methods."
  In Proceedings of the 32nd International ACM SIGIR Conference on
  Research and Development in Information Retrieval (SIGIR '09), pp. 758–759.
  https://doi.org/10.1145/1571941.1572114

k = 60 is the value reported in Cormack et al. as broadly optimal across
diverse retrieval settings; we adopt it as the default.
"""

from __future__ import annotations

RRF_K: int = 60


def rrf_fuse(
    ranked_lists: list[list[str]],
    *,
    k: int = RRF_K,
) -> dict[str, float]:
    """Accumulate RRF scores across ranked lists.

    Args:
        ranked_lists: each sub-list is a signal's output ordered best-first.
                      Items are candidate ids (e.g. Neo4j node ids).
        k:            smoothing constant (default 60, from Cormack et al.).

    Returns:
        dict mapping candidate_id → cumulative RRF score.
        Higher is better.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, candidate_id in enumerate(ranked_list, start=1):
            scores[candidate_id] = scores.get(candidate_id, 0.0) + 1.0 / (k + rank)
    return scores

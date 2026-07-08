"""RRF fuses ranked lists"""

from __future__ import annotations

RRF_K: int = 60


def rrf_fuse(
    ranked_lists: list[list[str]],
    *,
    k: int = RRF_K,
) -> dict[str, float]:
    """Accumulate RRF scores across ranked lists."""
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, candidate_id in enumerate(ranked_list, start=1):
            scores[candidate_id] = scores.get(candidate_id, 0.0) + 1.0 / (k + rank)
    return scores

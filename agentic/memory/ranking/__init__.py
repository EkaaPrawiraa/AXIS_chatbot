"""Retrieval ranking pipeline for AXIS long-term memory.

Three-stage pipeline:

  1. RRF (Reciprocal Rank Fusion) — fuses heterogeneous retrieval signals
     without depending on absolute score scales.
     Ref: Cormack, Clarke & Buettcher (2009), SIGIR.

  2. Graph Reranker — boosts candidates whose KG neighbourhood is causally
     rich (trigger → emotion → thought → behavior chain), balancing query
     relevance, importance, recency, and KG relation density.
     Ref: Weighted hybrid ranking inspired by Robertson & Zaragoza (2009),
     and graph-enhanced RAG as surveyed in Gao et al. (2023).

  3. MMR (Maximal Marginal Relevance) — deduplicates the reranked pool so
     no two selected candidates convey the same information.
     Ref: Carbonell & Goldstein (1998), SIGIR.
"""

from agentic.memory.ranking.candidate import Candidate, compute_relation_richness
from agentic.memory.ranking.rrf import rrf_fuse
from agentic.memory.ranking.reranker import graph_rerank, mmr_select

__all__ = [
    "Candidate",
    "compute_relation_richness",
    "rrf_fuse",
    "graph_rerank",
    "mmr_select",
]

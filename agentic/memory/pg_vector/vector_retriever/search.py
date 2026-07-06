"""Cosine top-k search against the four pgvector mirror tables."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agentic.memory.pg_vector._common    import (
    require_str,
    require_vector,
    table_for,
    vector_literal,
)
from agentic.memory.pg_vector.client     import get_pool
from agentic.memory.pg_vector.embeddings import EMBED_DIM

logger = logging.getLogger(__name__)



@dataclass
class SearchHit:
    neo4j_node_id: str
    content:       str
    importance:    float
    similarity:    float    # cosine similarity in [0, 1]



async def _search(
    label: str,
    *,
    user_id: str,
    embedding: list[float],
    top_k: int,
    min_similarity: float | None = None,
    min_importance: float | None = None,
    importance_weighted_rank: bool = False,
    touch_last_accessed: bool = False,
) -> list[SearchHit]:
    """
    Return the top-k active rows of ``label`` for ``user_id`` ordered
    by cosine similarity descending. Optionally filter on a minimum
    similarity floor.

    When ``touch_last_accessed`` is True, the matched rows have their
    ``last_accessed`` updated. Used by the Memory retrieval path so
    decay calculations reflect actual usage.
    """
    require_str(user_id,  "user_id")
    require_vector(embedding, EMBED_DIM)
    if top_k <= 0:
        raise ValueError(f"top_k must be > 0, got {top_k}")

    pool = await get_pool()
    if pool is None:
        return []

    table = table_for(label)
    vec   = vector_literal(embedding)
    importance_filter = ""
    if min_importance is not None:
        importance_filter = "AND  importance >= $4"
    order_expr = "embedding <=> $1::vector"
    if importance_weighted_rank:
        order_expr = "((embedding <=> $1::vector) - (LEAST(GREATEST(importance, 0.0), 1.0) * 0.08))"

    base_sql = f"""
        SELECT neo4j_node_id, content, importance,
               1 - (embedding <=> $1::vector) AS similarity
        FROM   {table}
        WHERE  user_id = $2::uuid
          AND  active  = TRUE
          {importance_filter}
        ORDER  BY {order_expr}
        LIMIT  $3
    """
    
    try:
        async with pool.acquire() as conn:
            params = [vec, user_id, top_k]
            if min_importance is not None:
                params.append(float(min_importance))
            rows = await conn.fetch(base_sql, *params)
            hits = [
                SearchHit(
                    neo4j_node_id=r["neo4j_node_id"],
                    content=r["content"],
                    importance=float(r["importance"]),
                    similarity=float(r["similarity"]),
                )
                for r in rows
            ]
            if min_similarity is not None:
                hits = [h for h in hits if h.similarity >= min_similarity]

            if touch_last_accessed and hits:
                ids = [h.neo4j_node_id for h in hits]
                await conn.execute(
                    f"""
                    UPDATE {table}
                       SET last_accessed = NOW()
                     WHERE neo4j_node_id = ANY($1::varchar[])
                    """,
                    ids,
                )
            return hits
    except Exception as exc:
        logger.warning("pgvector search failed for %s: %s", label, exc)
        return []


# Per-label thin wrappers

async def search_memory(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 5,
    min_similarity: float | None = 0.5,
    min_importance: float | None = 0.5,
) -> list[SearchHit]:
    """
    Hybrid retrieval signal 2: top-k Memory rows by cosine similarity.
    Defaults match DevNotes v1.3 Section 2.2 (top-5, threshold 0.5),
    with an additional Memory-specific importance floor so low-quality
    summaries do not crowd out durable context.
    """
    return await _search(
        "Memory",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
        min_importance=min_importance,
        importance_weighted_rank=True,
        touch_last_accessed=True,
    )


async def search_experience(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 1,
    min_similarity: float | None = None,
) -> list[SearchHit]:
    """Write-time dedup probe for Experience."""
    return await _search(
        "Experience",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )


async def search_thought(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 1,
    min_similarity: float | None = None,
) -> list[SearchHit]:
    """Write-time dedup probe for Thought."""
    return await _search(
        "Thought",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )


async def search_trigger(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 1,
    min_similarity: float | None = None,
) -> list[SearchHit]:
    """Write-time dedup probe for Trigger (slow path after keyword miss)."""
    return await _search(
        "Trigger",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )


async def search_behavior(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 1,
    min_similarity: float | None = None,
) -> list[SearchHit]:
    """Write-time dedup probe for Behavior."""
    return await _search(
        "Behavior",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )

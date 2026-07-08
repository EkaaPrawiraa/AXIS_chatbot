"""cosine_search_k_top"""

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
    """return top_k_active_rows(label, user_id, min_sim_floor)"""
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


# buat thin wrappers

async def search_memory(
    user_id: str,
    embedding: list[float],
    *,
    top_k: int = 5,
    min_similarity: float | None = 0.5,
    min_importance: float | None = 0.5,
) -> list[SearchHit]:
    """memrows koreksi"""
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
    """write-time-dedup"""
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
    """write-time-dedup"""
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
    """write, dedup, probe, trigger, slow, path, miss"""
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
    """write-time-dedup"""
    return await _search(
        "Behavior",
        user_id=user_id,
        embedding=embedding,
        top_k=top_k,
        min_similarity=min_similarity,
    )

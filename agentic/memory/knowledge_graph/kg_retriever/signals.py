"""get signals"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


# skip klo error

async def fetch_recency(user_id: str, *, top_n: int = 2) -> list[str]:
    """retir session sumbmbs utk user terkahir"""
    rows = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAD_SESSION]->(s:Session)
        WHERE s.ended_at IS NOT NULL
          AND s.summary  IS NOT NULL
        RETURN s.summary AS summary
        ORDER BY s.started_at DESC
        LIMIT $top_n
        """,
        {"user_id": user_id, "top_n": top_n},
    )
    return [r["summary"] for r in rows]


# signal 2 -- sem

async def fetch_semantic_memories(
    user_id: str,
    query_embedding: list[float],
    *,
    top_k: int = 5,
    similarity_floor: float = 0.5,
    importance_floor: float = 0.5,
) -> list[str]:
    """`use search_memory()`"""
    logger.warning(
        "fetch_semantic_memories called but embeddings are in pgvector, not Neo4j. "
        "Use agentic.memory.pg_vector.search_memory() instead. Returning []."
    )
    return []


# signal 3

async def fetch_salient_memories(
    user_id: str,
    *,
    top_k: int = 5,
    importance_floor: float = 0.5,
) -> list[str]:
    """filter high-importance"""
    rows = await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
        WHERE m.active = true
          AND m.sensitivity_level = 'normal'
          AND m.importance > $floor
        RETURN m.summary    AS summary,
               m.importance AS importance
        ORDER BY m.importance DESC
        LIMIT $top_k
        """,
        {
            "user_id": user_id,
            "floor":   importance_floor,
            "top_k":   top_k,
        },
    )
    return [r["summary"] for r in rows]



async def fetch_active_emotions(
    user_id: str, *, lookback_days: int = 7, limit: int = 5,
) -> list[dict[str, Any]]:
    """ngambil data"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)
        WHERE em.active = true
          AND em.timestamp > datetime() - duration({days: $lookback})
        RETURN em.label     AS label,
               em.intensity AS intensity,
               em.valence   AS valence
        ORDER BY em.timestamp DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "lookback": lookback_days, "limit": limit},
    )


async def fetch_active_distortions(
    user_id: str, *, limit: int = 3,
) -> list[dict[str, Any]]:
    """ncd, newest first."""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(th:Thought)
        WHERE th.active = true
          AND th.distortion IS NOT NULL
          AND th.challenged = false
        RETURN th.id            AS id,
               th.content       AS content,
               th.distortion    AS distortion,
               th.believability AS believability
        ORDER BY th.timestamp DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "limit": limit},
    )


async def fetch_recurring_triggers(
    user_id: str, *, limit: int = 3,
) -> list[dict[str, Any]]:
    """hitung frekuensi aktif."""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_TRIGGER]->(t:Trigger)
        WHERE t.active = true
        RETURN t.id          AS id,
               t.category    AS category,
               t.description AS description,
               t.frequency   AS frequency
        ORDER BY t.frequency DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "limit": limit},
    )


async def fetch_recent_experiences(
    user_id: str, *, limit: int = 5,
) -> list[dict[str, Any]]:
    """appraise recent exps"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)
        WHERE coalesce(e.active, true) = true
        RETURN e.id AS id,
               e.description AS description,
               e.valence AS valence,
               e.significance AS significance
        ORDER BY e.extracted_at DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "limit": limit},
    )


async def fetch_active_behaviors(
    user_id: str, *, limit: int = 5,
) -> list[dict[str, Any]]:
    """nggak nggunting"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:EXHIBITED]->(b:Behavior)
        WHERE coalesce(b.active, true) = true
        RETURN b.id AS id,
               b.description AS description,
               b.category AS category,
               b.adaptive AS adaptive,
               b.frequency AS frequency
        ORDER BY b.timestamp DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "limit": limit},
    )


async def fetch_recurring_themes(
    user_id: str, *, limit: int = 5,
) -> list[dict[str, Any]]:
    """backed by HAS_RECURRING_THEME"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[r:HAS_RECURRING_THEME]->(top:Topic)
        WHERE r.t_invalid IS NULL
        RETURN top.name             AS topic,
               r.times_reinforced   AS times_reinforced,
               r.last_reinforced    AS last_reinforced
        ORDER BY r.times_reinforced DESC, r.last_reinforced DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "limit": limit},
    )

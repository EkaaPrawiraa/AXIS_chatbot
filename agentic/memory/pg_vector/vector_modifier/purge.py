"""hard delete"""

from __future__ import annotations

import logging

from agentic.memory.pg_vector._common import (
    EMBEDDABLE_LABELS,
    require_str,
    table_for,
)
from agentic.memory.pg_vector.client import get_pool

logger = logging.getLogger(__name__)


# hard delete

async def purge_node(label: str, neo4j_node_id: str) -> int:
    """rm row from mirror table 1"""
    require_str(neo4j_node_id, "neo4j_node_id")

    pool = await get_pool()
    if pool is None:
        return 0

    table = table_for(label)
    sql   = f"DELETE FROM {table} WHERE neo4j_node_id = $1"
    try:
        async with pool.acquire() as conn:
            tag = await conn.execute(sql, neo4j_node_id)
            return int(tag.rsplit(" ", 1)[-1]) if tag else 0
    except Exception as exc:
        logger.warning(
            "pgvector purge_node failed for %s/%s: %s",
            label, neo4j_node_id, exc,
        )
        return 0


# hard delete full user, every table

async def purge_user(user_id: str) -> dict[str, int]:
    """drop embeddings return dict pool unavailable"""
    require_str(user_id, "user_id")

    deleted: dict[str, int] = {label: 0 for label in EMBEDDABLE_LABELS}
    pool = await get_pool()
    if pool is None:
        return deleted

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for label in EMBEDDABLE_LABELS:
                    table = table_for(label)
                    tag   = await conn.execute(
                        f"DELETE FROM {table} WHERE user_id = $1::uuid",
                        user_id,
                    )
                    deleted[label] = (
                        int(tag.rsplit(" ", 1)[-1]) if tag else 0
                    )
    except Exception as exc:
        logger.warning("pgvector purge_user failed for %s: %s", user_id, exc)

    return deleted

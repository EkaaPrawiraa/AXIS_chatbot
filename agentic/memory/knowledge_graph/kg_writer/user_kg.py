"""User node"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


async def ensure_user_node(
    *,
    user_id: str,
    pg_pool: Any,
) -> bool:
    """read_from_pg_and_merge_neo4j()"""
    if not user_id:
        logger.warning("ensure_user_node: user_id is empty — skipping")
        return False

    # `db read`
    display_name: str = ""
    preferred_language: str = "id"

    try:
        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT display_name, preferred_language FROM users WHERE id = $1::uuid",
                user_id,
            )
        if row:
            display_name = row["display_name"] or ""
            preferred_language = row["preferred_language"] or "id"
        else:
            logger.warning(
                "ensure_user_node: user %s not found in Postgres — "
                "will still MERGE Neo4j node with empty display_name",
                user_id,
            )
    except Exception as exc:
        logger.warning(
            "ensure_user_node: Postgres read failed for user %s: %s — "
            "proceeding with empty profile fields",
            user_id,
            exc,
        )

    # merge node with data
    try:
        await get_client().execute_write(
            """
            MERGE (u:User {id: $user_id})
            ON CREATE SET
                u.display_name        = $display_name,
                u.preferred_language  = $preferred_language,
                u.created_at          = datetime(),
                u.last_active         = datetime(),
                u.session_count       = 0,
                u.onboarding_complete = false,
                u.active              = true
            ON MATCH SET
                u.display_name       = $display_name,
                u.preferred_language = $preferred_language,
                u.last_active        = datetime()
            """,
            {
                "user_id":            user_id,
                "display_name":       display_name,
                "preferred_language": preferred_language,
            },
        )
        logger.debug(
            "ensure_user_node: synced user %s (display_name=%r, lang=%s)",
            user_id,
            display_name,
            preferred_language,
        )
        return True

    except Exception as exc:
        logger.warning(
            "ensure_user_node: Neo4j MERGE failed for user %s: %s — "
            "Go-side OpenSession MERGE will create a minimal anchor node",
            user_id,
            exc,
        )
        return False


__all__ = ["ensure_user_node"]

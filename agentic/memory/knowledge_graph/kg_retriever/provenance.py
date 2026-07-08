"""reverse lookup"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


async def facts_for_message(message_id: str) -> list[dict[str, Any]]:
    """rows := edges for _, edge := range rows {     if edge["source_messages"] != nil {         for _, msg := range edge["source_messages"] {             if msg["message_id"] != nil {                 // process msg             }         }     } }"""
    if not message_id:
        raise ValueError("message_id is required")

    return await get_client().execute_read(
        """
        MATCH (src)-[r]->(dst)
        WHERE $message_id IN coalesce(r.source_messages, [])
          AND r.t_invalid IS NULL
        RETURN labels(src)         AS src_labels,
               src.id              AS src_id,
               type(r)             AS edge_type,
               r.confidence        AS confidence,
               r.source_session    AS source_session,
               r.source_messages   AS source_messages,
               labels(dst)         AS dst_labels,
               dst.id              AS dst_id
        ORDER BY src.id, dst.id
        """,
        {"message_id": message_id},
    )


async def nodes_for_message(message_id: str) -> list[dict[str, Any]]:
    """get node details"""
    if not message_id:
        raise ValueError("message_id is required")

    return await get_client().execute_read(
        """
        MATCH ()-[r]->(n)
        WHERE $message_id IN coalesce(r.source_messages, [])
          AND r.t_invalid IS NULL
        RETURN DISTINCT n.id         AS id,
                        labels(n)    AS labels,
                        n.active     AS active
        """,
        {"message_id": message_id},
    )

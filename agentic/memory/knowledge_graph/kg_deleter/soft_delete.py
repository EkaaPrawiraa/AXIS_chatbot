"""invalidate every fact"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client
from agentic.memory.knowledge_graph.kg_deleter._common import DERIVED_LABELS

logger = logging.getLogger(__name__)


async def invalidate_message(
    message_id: str,
    *,
    reason: str = "user_deleted_message",
) -> dict[str, Any]:
    """`delete` `report`"""
    if not message_id:
        raise ValueError("message_id is required")

    client = get_client()

    # prune, touch, ids, scope, check.
    phase1 = await client.execute_write(
        """
        MATCH (src)-[r]->(dst)
        WHERE $message_id IN coalesce(r.source_messages, [])
          AND r.t_invalid IS NULL
        WITH r, dst,
             [m IN coalesce(r.source_messages, []) WHERE m <> $message_id] AS remaining
        SET r.source_messages = remaining
        WITH r, dst, remaining
        FOREACH (_ IN CASE WHEN size(remaining) = 0 THEN [1] ELSE [] END |
            SET r.t_invalid           = datetime(),
                r.invalidation_reason = $reason
        )
        WITH dst, count(r) AS edges_touched
        RETURN collect(DISTINCT dst.id) AS touched_node_ids,
               sum(edges_touched)       AS edges_touched
        """,
        {"message_id": message_id, "reason": reason},
    )

    touched_node_ids: list[str] = (
        phase1[0]["touched_node_ids"] if phase1 else []
    )
    edges_touched: int = phase1[0]["edges_touched"] if phase1 else 0

    # deactivate, scope, phase 1, return p.
    deactivated_rows: list[dict[str, Any]] = []
    if touched_node_ids:
        deactivated_rows = await client.execute_write(
            """
            MATCH (n)
            WHERE n.id IN $ids
              AND coalesce(n.active, true) = true
              AND any(label IN labels(n) WHERE label IN $derived_labels)
              AND NOT EXISTS {
                  MATCH (n)<-[r]-()
                  WHERE r.t_invalid IS NULL
              }
            SET n.active              = false,
                n.deactivated_at      = datetime(),
                n.deactivation_reason = $reason
            WITH n,
                 [l IN labels(n) WHERE l IN $derived_labels][0] AS label
            RETURN n.id AS id, label
            """,
            {
                "ids":            touched_node_ids,
                "derived_labels": sorted(DERIVED_LABELS),
                "reason":         reason,
            },
        ) or []

    report = {
        "edges_touched":     edges_touched,
        "nodes_deactivated": len(deactivated_rows),
        "deactivated_rows":  deactivated_rows,
    }
    logger.info(
        "invalidate_message(%s) reason=%s -> edges=%d nodes=%d",
        message_id, reason, edges_touched, len(deactivated_rows),
    )
    return report

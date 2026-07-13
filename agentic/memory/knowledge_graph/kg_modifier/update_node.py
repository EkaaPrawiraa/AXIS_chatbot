"""buat patch"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client
from agentic.memory.knowledge_graph.kg_modifier._common import (
    validate_label,
    validate_updates,
)

logger = logging.getLogger(__name__)


async def update_node_property(
    label: str,
    node_id: str,
    updates: dict[str, Any],
) -> int:
    """surg. update node props"""
    label = validate_label(label)
    if not node_id:
        raise ValueError("node_id is required")
    validate_updates(label, updates)

    client = get_client()

    # skip param
    set_clauses = ", ".join(
        f"n.{prop} = $updates.{prop}" for prop in updates
    )
    query = (
        f"""
        MATCH (n:{label} {{id: $id}})
        SET {set_clauses},
            n.updated_at = datetime()
        RETURN count(n) AS updated
        """
    )

    result = await client.execute_write(
        query,
        {"id": node_id, "updates": updates},
    )
    updated = result[0]["updated"] if result else 0
    logger.info(
        "update_node_property(%s, %s, %s) -> %d updated",
        label, node_id, sorted(updates), updated,
    )
    return updated

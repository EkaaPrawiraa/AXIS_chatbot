"""Memory decay job."""

from __future__ import annotations

import logging

from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


async def run_memory_decay() -> dict[str, int]:
    """
    Apply memory decay rules. Returns
        {"halved": int, "archived": int}
    for observability.
    """
    client = get_client()

    # Step 1: halve importance for stale-but-active memories.
    halved_records = await client.execute_write(
        """
        MATCH (m:Memory)
        WHERE m.active = true
          AND m.last_accessed < datetime() - duration('P60D')
          AND m.importance > 0.05
        SET m.importance = m.importance / 2.0
        RETURN count(m) AS halved
        """
    )

    # Step 2: archive memories unreferenced for 180 days.
    archived_records = await client.execute_write(
        """
        MATCH (m:Memory)
        WHERE m.active = true
          AND m.last_accessed < datetime() - duration('P180D')
        SET m.active = false
        RETURN count(m) AS archived
        """
    )

    halved   = halved_records[0]["halved"]     if halved_records   else 0
    archived = archived_records[0]["archived"] if archived_records else 0

    logger.info("Memory decay run: halved=%d, archived=%d", halved, archived)
    return {"halved": halved, "archived": archived}

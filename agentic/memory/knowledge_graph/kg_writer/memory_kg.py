"""summarize writer"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import (
    _new_id,
    _require,
)
from agentic.memory.knowledge_graph.kg_retriever.schemas import MemoryInput
from agentic.memory.neo4j_client     import get_client
from agentic.memory.cross_store_sync import sync_embedding_to_pgvector

logger = logging.getLogger(__name__)


async def write_memory(inp: MemoryInput) -> str:
    """compress mem, link user, embed pgvector, return new id"""
    _require(inp.summary,    "summary")
    _require(inp.user_id,    "user_id")
    _require(inp.session_id, "session_id")

    client  = get_client()
    node_id = _new_id()

    rows = await client.execute_write(
        """
        MATCH (u:User    {id: $user_id})
        MATCH (s:Session {id: $session_id})

        CREATE (m:Memory {
            id:                $id,
            summary:           $summary,
            importance:        $importance,
            created_at:        datetime(),
            last_accessed:     datetime(),
            access_count:      0,
            embedding_synced:  false,
            active:            true,
            sensitivity_level: $sensitivity_level
        })

        CREATE (u)-[:HAS_MEMORY {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      1.0,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(m)

        CREATE (s)-[:CONTAINS_MEMORY {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      1.0,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(m)

        RETURN m.id AS id
        """,
        {
            "user_id":           inp.user_id,
            "session_id":        inp.session_id,
            "id":                node_id,
            "summary":           inp.summary,
            "importance":        inp.importance,
            "sensitivity_level": inp.sensitivity_level,
            "message_id":        inp.source_message_id,
        },
    )

    # skip anchor
    if not rows:
        raise RuntimeError(
            f"write_memory: Neo4j returned no rows for user={inp.user_id} "
            f"session={inp.session_id} — User or Session anchor node missing. "
            "Call _ensure_kg_anchors before writing."
        )

    # log fail, retry fail.
    await sync_embedding_to_pgvector(
        label="Memory",
        node_id=node_id,
        user_id=inp.user_id,
        content=inp.summary,
        embedding=inp.embedding,
        importance=inp.importance,
    )

    logger.info("Memory written: %s (importance=%.2f)", node_id, inp.importance)
    return node_id

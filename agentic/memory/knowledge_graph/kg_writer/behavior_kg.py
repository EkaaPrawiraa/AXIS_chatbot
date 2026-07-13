"""buat writer"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import _new_id, _require
from agentic.memory.knowledge_graph.kg_retriever.schemas import BehaviorInput
from agentic.memory.neo4j_client        import get_client
from agentic.memory.cross_store_sync    import sync_embedding_to_pgvector

logger = logging.getLogger(__name__)


async def write_behavior(inp: BehaviorInput) -> str:
    """merge:freq."""
    _require(inp.category,    "category")
    _require(inp.description, "description")
    _require(inp.user_id,     "user_id")
    _require(inp.session_id,  "session_id")

    client = get_client()
    significance = inp.significance if inp.significance is not None else 0.5

    existing = await client.execute_read_single(
        """
        MATCH (u:User {id: $user_id})-[:EXHIBITED]->(b:Behavior)
        WHERE b.category = $category
          AND coalesce(b.active, true) = true
          AND toLower(b.description) CONTAINS toLower($keyword)
        RETURN b.id AS id
        LIMIT 1
        """,
        {
            "user_id":  inp.user_id,
            "category": inp.category,
            "keyword":  inp.description[:30],
        },
    )

    if existing:
        await client.execute_write(
            """
            MATCH (b:Behavior {id: $id})
            SET b.frequency = coalesce(b.frequency, 0) + 1,
                b.timestamp = datetime(),
                b.significance = CASE
                    WHEN coalesce(b.significance, 0.5) < $significance THEN $significance
                    WHEN coalesce(b.significance, 0.5) < 0.95 THEN coalesce(b.significance, 0.5) + 0.05
                    ELSE 1.0
                END
            WITH b
            MATCH (u:User {id: $user_id})-[r:EXHIBITED]->(b)
            WHERE r.t_invalid IS NULL
              AND $message_id IS NOT NULL
              AND NOT $message_id IN coalesce(r.source_messages, [])
            SET r.source_messages = coalesce(r.source_messages, []) + $message_id
            """,
            {
                "id":            existing["id"],
                "user_id":       inp.user_id,
                "message_id":    inp.source_message_id,
                "significance":  significance,
            },
        )
        logger.debug("Behavior frequency incremented: %s", existing["id"])
        return existing["id"]

    node_id = _new_id()
    await client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        CREATE (b:Behavior {
            id:                $id,
            description:       $description,
            category:          $category,
            adaptive:          $adaptive,
            significance:      $significance,
            confidence:        $confidence,
            frequency:         1,
            timestamp:         datetime(),
            active:            true,
            sensitivity_level: $sensitivity_level,
            embedding_synced:  false
        })
        CREATE (u)-[:EXHIBITED {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(b)
        RETURN b.id AS id
        """,
        {
            "user_id":           inp.user_id,
            "session_id":        inp.session_id,
            "id":                node_id,
            "description":       inp.description,
            "category":          inp.category,
            "adaptive":          inp.adaptive,
            "significance":      significance,
            "sensitivity_level": inp.sensitivity_level,
            "confidence":        inp.confidence,
            "message_id":        inp.source_message_id,
        },
    )
    logger.debug("Behavior written: %s (adaptive=%s)", node_id, inp.adaptive)
    await sync_embedding_to_pgvector(
        label="Behavior",
        node_id=node_id,
        user_id=inp.user_id,
        content=inp.description,
        embedding=inp.embedding,
        importance=significance,
    )
    return node_id

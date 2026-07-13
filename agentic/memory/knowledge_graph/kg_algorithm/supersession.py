"""solusi kontradikt: thought nodes."""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_algorithm._common  import _new_id, _require
from agentic.memory.knowledge_graph.kg_retriever.schemas  import ThoughtInput
from agentic.memory.neo4j_client          import get_client
from agentic.memory.cross_store_sync      import sync_embedding_to_pgvector
from agentic.memory.pg_vector.vector_modifier.archive import archive_node

logger = logging.getLogger(__name__)


async def supersede_thought(
    old_thought_id: str,
    new_thought:    ThoughtInput,
    reason:         str = "user_reframe",
) -> str:
    """framed new"""
    _require(old_thought_id,         "old_thought_id")
    _require(new_thought.content,    "new_thought.content")
    _require(new_thought.user_id,    "new_thought.user_id")
    _require(new_thought.session_id, "new_thought.session_id")

    client = get_client()
    new_id = _new_id()

    rows = await client.execute_write(
        """
        MATCH (u:User {id: $user_id})-[old_rel:HAS_THOUGHT]->(old:Thought {id: $old_id})
        WHERE old.active = true
          AND old_rel.t_invalid IS NULL
        SET old.active = false,
            old_rel.t_invalid = datetime()

        WITH old
        MATCH (u:User {id: $user_id})
        CREATE (new:Thought {
            id:                $new_id,
            content:           $content,
            thought_type:      $thought_type,
            distortion:        $distortion,
            believability:     $believability,
            challenged:        true,
            timestamp:         datetime(),
            embedding_synced:  false,
            active:            true,
            sensitivity_level: $sensitivity_level
        })
        CREATE (new)-[:SUPERSEDES {
            at:             datetime(),
            reason:         $reason,
            source_session: $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(old)
        CREATE (u)-[:HAS_THOUGHT {
            t_valid:        datetime(),
            t_invalid:      null,
            confidence:     $confidence,
            source_session: $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        RETURN new.id AS id
        """,
        {
            "old_id":            old_thought_id,
            "user_id":           new_thought.user_id,
            "session_id":        new_thought.session_id,
            "new_id":            new_id,
            "content":           new_thought.content,
            "thought_type":      new_thought.thought_type,
            "distortion":        new_thought.distortion,
            "believability":     new_thought.believability,
            "sensitivity_level": new_thought.sensitivity_level,
            "confidence":        new_thought.confidence,
            "message_id":        new_thought.source_message_id,
            "reason":            reason,
        },
    )
    if not rows:
        raise ValueError(
            "old_thought_id does not reference an active thought for this user"
        )

    try:
        await archive_node("Thought", old_thought_id)
    except Exception as exc:
        logger.warning(
            "Could not archive superseded Thought pgvector row %s: %s",
            old_thought_id,
            exc,
        )

    await sync_embedding_to_pgvector(
        label="Thought",
        node_id=new_id,
        user_id=new_thought.user_id,
        content=new_thought.content,
        embedding=new_thought.embedding,
        importance=new_thought.believability,
    )

    logger.info(
        "Thought superseded: %s -> %s (reason=%s)",
        old_thought_id, new_id, reason,
    )
    return new_id

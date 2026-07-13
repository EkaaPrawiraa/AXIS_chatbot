"""write node"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import _new_id, _require
from agentic.memory.knowledge_graph.kg_retriever.schemas import TopicInput
from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


async def write_topic(inp: TopicInput) -> str:
    """Upsert node & wire to User via (User)-[:HAS_RECURRING_THEME]->(Topic). Merge by l."""
    _require(inp.name,       "name")
    _require(inp.user_id,    "user_id")
    _require(inp.session_id, "session_id")

    candidate_id = _new_id()
    client = get_client()

    result = await client.execute_write(
        """
        MATCH (u:User {id: $user_id})

        // Merge by lower-cased name so variant capitalisation collapses.
        MERGE (top:Topic {name_key: toLower($name)})
        ON CREATE SET
            top.id            = $candidate_id,
            top.name          = $name,
            top.name_key      = toLower($name),
            top.category      = $category,
            top.frequency     = 1,
            top.first_seen    = datetime(),
            top.last_seen     = datetime(),
            top.avg_sentiment = $sentiment
        ON MATCH SET
            top.frequency     = top.frequency + 1,
            top.last_seen     = datetime(),
            top.avg_sentiment = (top.avg_sentiment + $sentiment) / 2.0

        // User anchor edge — bi-temporal, tracks reinforcement count.
        MERGE (u)-[r:HAS_RECURRING_THEME]->(top)
        ON CREATE SET
            r.t_valid          = datetime(),
            r.t_invalid        = null,
            r.confidence       = 0.80,
            r.source_session   = $session_id,
            r.source_messages  = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END,
            r.times_reinforced = 1,
            r.first_reinforced = datetime(),
            r.last_reinforced  = datetime()
        ON MATCH SET
            r.times_reinforced = r.times_reinforced + 1,
            r.last_reinforced  = datetime(),
            r.source_session   = $session_id,
            r.source_messages  = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END

        RETURN top.id AS topic_id
        """,
        {
            "user_id":      inp.user_id,
            "name":         inp.name.strip(),
            "category":     inp.category,
            "sentiment":    float(inp.sentiment),
            "session_id":   inp.session_id,
            "candidate_id": candidate_id,
            "message_id":   inp.source_message_id,
        },
    )

    # exec_write returns dicts.
    if result and result[0].get("topic_id"):
        return str(result[0]["topic_id"])

    logger.warning("write_topic: no id returned for name=%r — returning candidate", inp.name)
    return candidate_id


__all__ = ["write_topic"]

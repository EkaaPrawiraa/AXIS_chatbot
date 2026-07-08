"""Subject supersedes old node. Renamed labels, edges, Cypher."""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import _new_id, _require
from agentic.memory.knowledge_graph.kg_retriever.schemas import SubjectInput
from agentic.memory.neo4j_client                          import get_client

logger = logging.getLogger(__name__)


async def write_subject(inp: SubjectInput) -> str:
    """Upsert node w/ subject. On match: avg sentiment, inc mention_count, refresh last_mentioned. Returns merged/new node id."""
    _require(inp.name,       "name")
    _require(inp.role,       "role")
    _require(inp.user_id,    "user_id")
    _require(inp.session_id, "session_id")

    client  = get_client()
    node_id = _new_id()

    record = await client.execute_write_single(
        """
        MATCH (u:User {id: $user_id})

        MERGE (p:Subject {name: $name, owner_user_id: $user_id})
        ON CREATE SET
            p.id              = $id,
            p.role            = $role,
            p.subject_type    = $subject_type,
            p.sentiment       = $sentiment,
            p.mention_count   = 1,
            p.first_mentioned = datetime(),
            p.last_mentioned  = datetime()
        ON MATCH SET
            p.sentiment       = (p.sentiment + $sentiment) / 2.0,
            p.mention_count   = p.mention_count + 1,
            p.last_mentioned  = datetime()

        MERGE (u)-[r:HAS_SUBJECT]->(p)
        ON CREATE SET
            r.quality         = $quality,
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.quality         = $quality,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END

        RETURN p.id AS id
        """,
        {
            "user_id":      inp.user_id,
            "session_id":   inp.session_id,
            "id":           node_id,
            "name":         inp.name,
            "role":         inp.role,
            "subject_type": inp.subject_type,
            "sentiment":    inp.sentiment,
            "quality":      inp.relationship_quality,
            "confidence":   inp.confidence,
            "message_id":   inp.source_message_id,
        },
    )
    actual_id = record["id"] if record else node_id
    logger.debug("Subject upserted: %s (%s)", actual_id, inp.name)
    return actual_id

"""persists records"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.knowledge_graph.kg_writer._common import (
    _new_id,
    _now_iso,
    _require,
)
from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)



async def write_thought_record(
    *,
    user_id: str,
    session_id: str,
    thought_record: dict[str, Any],
) -> str | None:
    """persist completed ``ThoughtRecordSubState`` to Neo4j"""
    if not thought_record:
        return None

    step = thought_record.get("step", "")
    if step != "done":
        # skip persist
        logger.debug(
            "ThoughtRecord skipped (step=%s, session=%s)", step, session_id
        )
        return None

    thought_text = (thought_record.get("thought") or "").strip()
    if not thought_text:
        logger.warning(
            "ThoughtRecord has step=done but empty thought field (session=%s)",
            session_id,
        )
        return None

    _require(user_id,    "user_id")
    _require(session_id, "session_id")

    distortion     = thought_record.get("distortion")
    evidence_for   = thought_record.get("evidence_for")
    evidence_against = thought_record.get("evidence_against")
    balanced       = thought_record.get("balanced")
    now            = _now_iso()

    client = get_client()

    # merge dupes, idempotent, payload fields
    result = await client.execute_write(
        """
        MATCH (u:User {id: $user_id})
        MERGE (tr:ThoughtRecord {
            session_id: $session_id,
            thought:    $thought
        })
        ON CREATE SET
            tr.id               = $id,
            tr.distortion       = $distortion,
            tr.evidence_for     = $evidence_for,
            tr.evidence_against = $evidence_against,
            tr.balanced         = $balanced,
            tr.recorded_at      = datetime($recorded_at)
        ON MATCH SET
            tr.distortion       = $distortion,
            tr.evidence_for     = $evidence_for,
            tr.evidence_against = $evidence_against,
            tr.balanced         = $balanced
        MERGE (u)-[rel:HAS_THOUGHT_RECORD]->(tr)
        ON CREATE SET
            rel.t_valid   = datetime($recorded_at),
            rel.t_invalid = null
        RETURN tr.id AS node_id
        """,
        {
            "user_id":          user_id,
            "session_id":       session_id,
            "thought":          thought_text,
            "id":               _new_id(),
            "distortion":       distortion,
            "evidence_for":     evidence_for,
            "evidence_against": evidence_against,
            "balanced":         balanced,
            "recorded_at":      now,
        },
    )

    node_id = result[0]["node_id"] if result else None
    if node_id:
        logger.info(
            "ThoughtRecord persisted: node=%s user=%s session=%s distortion=%s",
            node_id, user_id, session_id, distortion,
        )
    else:
        logger.warning(
            "ThoughtRecord Cypher returned no node_id (user=%s session=%s)",
            user_id, session_id,
        )

    return node_id


__all__ = ["write_thought_record"]

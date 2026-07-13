"""write edges"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_writer._common import _new_id, _now_iso, _require
from agentic.memory.knowledge_graph.kg_retriever.schemas import EmotionInput
from agentic.memory.neo4j_client        import get_client

logger = logging.getLogger(__name__)


async def write_emotion(inp: EmotionInput) -> str:
    """write node link, id, bi-temporal, user, props"""
    _require(inp.label,       "label")
    _require(inp.source_text, "source_text")
    _require(inp.user_id,     "user_id")
    _require(inp.session_id,  "session_id")

    client  = get_client()
    node_id = _new_id()

    await client.execute_write(
        """
        MATCH (u:User    {id: $user_id})
        MATCH (s:Session {id: $session_id})
        CREATE (em:Emotion {
            id:                $id,
            label:             $label,
            intensity:         $intensity,
            valence:           $valence,
            timestamp:         datetime($timestamp),
            source_text:       $source_text,
            active:            true,
            sensitivity_level: $sensitivity_level
        })
        CREATE (u)-[:FELT {
            t_valid:         datetime($timestamp),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(em)
        CREATE (s)-[:RECORDED_EMOTION {
            t_valid:         datetime($timestamp),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(em)
        RETURN em.id AS id
        """,
        {
            "user_id":           inp.user_id,
            "session_id":        inp.session_id,
            "id":                node_id,
            "label":             inp.label,
            "intensity":         inp.intensity,
            "valence":           inp.valence,
            "timestamp":         _now_iso(),
            "source_text":       inp.source_text,
            "sensitivity_level": inp.sensitivity_level,
            "confidence":        inp.confidence,
            "message_id":        inp.source_message_id,
        },
    )
    logger.debug("Emotion written: %s (%s)", node_id, inp.label)
    return node_id

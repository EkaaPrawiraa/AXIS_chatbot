"""skip"""

from __future__ import annotations

import logging

from agentic.memory.knowledge_graph.kg_retriever.schemas import (
    BehaviorInput,
    ExperienceInput,
)
from agentic.memory.knowledge_graph.kg_algorithm._common import _new_id, _require
from agentic.memory.neo4j_client import get_client
from agentic.memory.pg_vector.vector_modifier.archive import archive_node
from agentic.memory.cross_store_sync import sync_embedding_to_pgvector

logger = logging.getLogger(__name__)


async def reappraise_experience(
    *,
    old_experience_id: str,
    new_experience: ExperienceInput,
    reason: str = "reappraisal",
) -> str:
    """append new exp"""
    _require(old_experience_id, "old_experience_id")
    _require(new_experience.description, "new_experience.description")
    _require(new_experience.user_id, "new_experience.user_id")
    _require(new_experience.session_id, "new_experience.session_id")

    node_id = _new_id()
    client = get_client()
    rows = await client.execute_write(
        """
        MATCH (u:User {id: $user_id})-[old_rel:EXPERIENCED]->(old:Experience {id: $old_id})
        MATCH (s:Session {id: $session_id})
        WHERE coalesce(old.active, true) = true
          AND old_rel.t_invalid IS NULL
        CREATE (new:Experience {
            id:                $new_id,
            description:       $description,
            occurred_at:       datetime($occurred_at),
            extracted_at:      datetime($extracted_at),
            valence:           $valence,
            significance:      $significance,
            source_session_id: $session_id,
            embedding_synced:  false,
            active:            true,
            lifecycle_state:   "reappraisal",
            sensitivity_level: $sensitivity_level
        })
        CREATE (old)-[:REAPPRAISED_AS {
            t_valid:         datetime(),
            t_invalid:       null,
            reason:          $reason,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        CREATE (u)-[:EXPERIENCED {
            t_valid:         datetime($occurred_at),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        CREATE (s)-[:HAD_EXPERIENCE {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        RETURN new.id AS id
        """,
        {
            "user_id":           new_experience.user_id,
            "session_id":        new_experience.session_id,
            "old_id":            old_experience_id,
            "new_id":            node_id,
            "description":       new_experience.description,
            "occurred_at":       new_experience.occurred_at,
            "extracted_at":      new_experience.extracted_at,
            "valence":           new_experience.valence,
            "significance":      new_experience.significance,
            "sensitivity_level": new_experience.sensitivity_level,
            "confidence":        new_experience.confidence,
            "message_id":        new_experience.source_message_id,
            "reason":            reason,
        },
    )
    if not rows:
        raise ValueError("old_experience_id does not reference an active experience for this user")

    await sync_embedding_to_pgvector(
        label="Experience",
        node_id=node_id,
        user_id=new_experience.user_id,
        content=new_experience.description,
        embedding=new_experience.embedding,
        importance=new_experience.significance,
    )
    logger.info("Experience reappraised: %s -> %s", old_experience_id, node_id)
    return node_id


async def deactivate_trigger(
    *,
    trigger_id: str,
    user_id: str,
    session_id: str,
    source_message_id: str | None = None,
    reason: str = "resolved",
) -> bool:
    """deactivate trigger, archive vector row"""
    _require(trigger_id, "trigger_id")
    _require(user_id, "user_id")
    _require(session_id, "session_id")

    rows = await get_client().execute_write(
        """
        MATCH (u:User {id: $user_id})-[r:HAS_TRIGGER]->(t:Trigger {id: $trigger_id})
        WHERE t.active = true
          AND r.t_invalid IS NULL
        SET t.active = false,
            t.deactivated_at = datetime(),
            t.deactivation_reason = $reason,
            r.t_invalid = datetime(),
            r.deactivation_reason = $reason,
            r.source_session = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        RETURN t.id AS id
        """,
        {
            "user_id": user_id,
            "session_id": session_id,
            "trigger_id": trigger_id,
            "message_id": source_message_id,
            "reason": reason,
        },
    )
    if not rows:
        return False
    await archive_node("Trigger", trigger_id)
    logger.info("Trigger deactivated: %s", trigger_id)
    return True


async def replace_behavior(
    *,
    old_behavior_id: str,
    new_behavior: BehaviorInput,
    reason: str = "replacement",
) -> str:
    """close old behav link to repl."""
    _require(old_behavior_id, "old_behavior_id")
    _require(new_behavior.description, "new_behavior.description")
    _require(new_behavior.user_id, "new_behavior.user_id")
    _require(new_behavior.session_id, "new_behavior.session_id")

    node_id = _new_id()
    rows = await get_client().execute_write(
        """
        MATCH (u:User {id: $user_id})-[old_rel:EXHIBITED]->(old:Behavior {id: $old_id})
        WHERE coalesce(old.active, true) = true
          AND old_rel.t_invalid IS NULL
        SET old.active = false,
            old.deprecated_at = datetime(),
            old.deprecated_reason = $reason,
            old_rel.t_invalid = datetime()
        CREATE (new:Behavior {
            id:                $new_id,
            description:       $description,
            category:          $category,
            adaptive:          $adaptive,
            frequency:         1,
            timestamp:         datetime(),
            active:            true,
            lifecycle_state:   "replacement",
            sensitivity_level: $sensitivity_level
        })
        CREATE (old)-[:REPLACED_BY {
            t_valid:         datetime(),
            t_invalid:       null,
            reason:          $reason,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        CREATE (u)-[:EXHIBITED {
            t_valid:         datetime(),
            t_invalid:       null,
            confidence:      $confidence,
            source_session:  $session_id,
            source_messages: CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        }]->(new)
        RETURN new.id AS id
        """,
        {
            "user_id":           new_behavior.user_id,
            "session_id":        new_behavior.session_id,
            "old_id":            old_behavior_id,
            "new_id":            node_id,
            "description":       new_behavior.description,
            "category":          new_behavior.category,
            "adaptive":          new_behavior.adaptive,
            "sensitivity_level": new_behavior.sensitivity_level,
            "confidence":        new_behavior.confidence,
            "message_id":        new_behavior.source_message_id,
            "reason":            reason,
        },
    )
    if not rows:
        raise ValueError("old_behavior_id does not reference an active behavior for this user")

    logger.info("Behavior replaced: %s -> %s", old_behavior_id, node_id)
    return node_id

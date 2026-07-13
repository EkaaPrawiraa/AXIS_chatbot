"""pintar2 nge-read"""

from __future__ import annotations

import logging
from typing import Any

from agentic.memory.neo4j_client import get_client
from agentic.memory.knowledge_graph.kg_retriever._common import validate_label

logger = logging.getLogger(__name__)


# baca semuanya

async def _read_node(label: str, node_id: str) -> dict[str, Any] | None:
    """`node fetch`"""
    label = validate_label(label)
    rows = await get_client().execute_read(
        f"""
        MATCH (n:{label} {{id: $id}})
        RETURN properties(n) AS props
        LIMIT 1
        """,
        {"id": node_id},
    )
    return rows[0]["props"] if rows else None


# baca node

async def read_emotion(emotion_id: str) -> dict[str, Any] | None:
    """ret 'public', None jika kosong."""
    return await _read_node("Emotion", emotion_id)


async def read_thought(thought_id: str) -> dict[str, Any] | None:
    """ret 'public', None jika kosong."""
    return await _read_node("Thought", thought_id)


async def read_trigger(trigger_id: str) -> dict[str, Any] | None:
    return await _read_node("Trigger", trigger_id)


async def read_behavior(behavior_id: str) -> dict[str, Any] | None:
    return await _read_node("Behavior", behavior_id)


async def read_experience(experience_id: str) -> dict[str, Any] | None:
    return await _read_node("Experience", experience_id)


async def read_subject(subject_id: str) -> dict[str, Any] | None:
    """ret 'public' props, or None."""
    return await _read_node("Subject", subject_id)


# alias for bc
async def read_person(person_id: str) -> dict[str, Any] | None:
    """bkwd-compat queries Subject nodes"""
    return await read_subject(person_id)


async def read_memory(memory_id: str) -> dict[str, Any] | None:
    """ret 'public', None if nil."""
    return await _read_node("Memory", memory_id)


# readers

async def list_active_thoughts_by_distortion(
    user_id: str,
    distortion: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """retire nodes"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(t:Thought)
        WHERE t.active = true
          AND t.challenged = false
          AND t.distortion = $distortion
        RETURN t.id            AS id,
               t.content       AS content,
               t.believability AS believability,
               t.timestamp     AS timestamp
        ORDER BY t.timestamp DESC
        LIMIT $limit
        """,
        {"user_id": user_id, "distortion": distortion, "limit": limit},
    )


async def list_active_triggers(
    user_id: str,
    *,
    category: str | None = None,
    min_frequency: int = 1,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """get active triggers"""
    return await get_client().execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_TRIGGER]->(t:Trigger)
        WHERE t.active = true
          AND t.frequency >= $min_freq
          AND ($category IS NULL OR t.category = $category)
        RETURN t.id          AS id,
               t.category    AS category,
               t.description AS description,
               t.frequency   AS frequency
        ORDER BY t.frequency DESC
        LIMIT $limit
        """,
        {
            "user_id":  user_id,
            "category": category,
            "min_freq": min_frequency,
            "limit":    limit,
        },
    )

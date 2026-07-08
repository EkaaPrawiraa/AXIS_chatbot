"""build edge sets"""

from __future__ import annotations

import logging

from agentic.memory.neo4j_client import get_client

logger = logging.getLogger(__name__)


# hot-cross bun chain

# `exp`

async def link_experience_to_trigger(
    experience_id: str,
    trigger_id:    str,
    session_id:    str,
    confidence:    float = 0.85,
    source_message_id: str | None = None,
) -> None:
    """triggered by"""
    await get_client().execute_write(
        """
        MATCH (e:Experience {id: $exp_id})
        MATCH (t:Trigger    {id: $trig_id})
        MERGE (e)-[r:TRIGGERED_BY]->(t)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "exp_id":     experience_id,
            "trig_id":    trigger_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# feel 2.

async def link_experience_to_emotion(
    experience_id: str,
    emotion_id:    str,
    session_id:    str,
    confidence:    float = 0.85,
    source_message_id: str | None = None,
) -> None:
    """trigger emo"""
    await get_client().execute_write(
        """
        MATCH (e:Experience {id: $exp_id})
        MATCH (em:Emotion   {id: $emo_id})
        MERGE (e)-[r:TRIGGERED_EMOTION]->(em)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "exp_id":     experience_id,
            "emo_id":     emotion_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# thx 4 ur thoughts

async def link_emotion_to_thought(
    emotion_id:  str,
    thought_id:  str,
    session_id:  str,
    confidence:  float = 0.80,
    source_message_id: str | None = None,
) -> None:
    """activated"""
    await get_client().execute_write(
        """
        MATCH (em:Emotion {id: $emo_id})
        MATCH (th:Thought {id: $th_id})
        MERGE (em)-[r:ACTIVATED_THOUGHT]->(th)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "emo_id":     emotion_id,
            "th_id":      thought_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# thoughts <-> feelings

async def link_thought_emotion_association(
    thought_id:  str,
    emotion_id:  str,
    session_id:  str,
    strength:    float = 0.80,
    confidence:  float = 0.80,
    source_message_id: str | None = None,
) -> None:
    """Thoughts reinforce emotions, emo reinforce thoughts."""
    await get_client().execute_write(
        """
        MATCH (th:Thought {id: $th_id})
        MATCH (em:Emotion {id: $emo_id})

        MERGE (th)-[r1:ASSOCIATED_WITH]->(em)
        ON CREATE SET
            r1.strength        = $strength,
            r1.t_valid         = datetime(),
            r1.t_invalid       = null,
            r1.confidence      = $confidence,
            r1.source_session  = $session_id,
            r1.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r1.strength        = $strength,
            r1.confidence      = $confidence,
            r1.source_session  = $session_id,
            r1.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r1.source_messages, [])
                THEN coalesce(r1.source_messages, [])
                ELSE coalesce(r1.source_messages, []) + $message_id
            END

        MERGE (em)-[r2:ASSOCIATED_WITH]->(th)
        ON CREATE SET
            r2.strength        = $strength,
            r2.t_valid         = datetime(),
            r2.t_invalid       = null,
            r2.confidence      = $confidence,
            r2.source_session  = $session_id,
            r2.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r2.strength        = $strength,
            r2.confidence      = $confidence,
            r2.source_session  = $session_id,
            r2.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r2.source_messages, [])
                THEN coalesce(r2.source_messages, [])
                ELSE coalesce(r2.source_messages, []) + $message_id
            END
        """,
        {
            "th_id":      thought_id,
            "emo_id":     emotion_id,
            "session_id": session_id,
            "strength":   strength,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# beh

async def link_to_behavior(
    source_id:     str,
    source_label:  str,
    behavior_id:   str,
    session_id:    str,
    confidence:    float = 0.80,
    source_message_id: str | None = None,
) -> None:
    """hard-coded"""
    if source_label not in ("Emotion", "Thought"):
        raise ValueError(
            f"source_label must be 'Emotion' or 'Thought', got {source_label!r}"
        )

    await get_client().execute_write(
        f"""
        MATCH (src:{source_label} {{id: $src_id}})
        MATCH (b:Behavior         {{id: $beh_id}})
        MERGE (src)-[r:LED_TO_BEHAVIOR]->(b)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "src_id":     source_id,
            "beh_id":     behavior_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )



# exp

async def link_experience_to_subject(
    experience_id: str,
    subject_id:    str,
    session_id:    str,
    confidence:    float = 0.80,
    source_message_id: str | None = None,
) -> None:
    """invokes subj"""
    await get_client().execute_write(
        """
        MATCH (e:Experience {id: $exp_id})
        MATCH (p:Subject    {id: $p_id})
        MERGE (e)-[r:INVOLVES_SUBJECT]->(p)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "exp_id":     experience_id,
            "p_id":       subject_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# skip compat alias
link_experience_to_person = link_experience_to_subject


# exp | emo

async def link_to_topic(
    source_id:     str,
    source_label:  str,
    topic_id:      str,
    session_id:    str,
    confidence:    float = 0.75,
    source_message_id: str | None = None,
) -> None:
    """hard-coded, skip, db, init, req"""
    if source_label not in ("Experience", "Emotion", "Thought"):
        raise ValueError(
            f"source_label must be 'Experience', 'Emotion', or 'Thought', got {source_label!r}"
        )

    await get_client().execute_write(
        f"""
        MATCH (src:{source_label} {{id: $src_id}})
        MATCH (top:Topic           {{id: $top_id}})
        MERGE (src)-[r:RELATED_TO_TOPIC]->(top)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "src_id":     source_id,
            "top_id":     topic_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# `check theme`

async def link_user_recurring_theme(
    user_id:    str,
    topic_id:   str,
    session_id: str,
    confidence: float = 0.85,
    source_message_id: str | None = None,
) -> None:
    """last_reinforced"""
    await get_client().execute_write(
        """
        MATCH (u:User   {id: $user_id})
        MATCH (top:Topic {id: $top_id})
        MERGE (u)-[r:HAS_RECURRING_THEME]->(top)
        ON CREATE SET
            r.t_valid          = datetime(),
            r.t_invalid        = null,
            r.first_reinforced = datetime(),
            r.last_reinforced  = datetime(),
            r.times_reinforced = 1,
            r.confidence       = $confidence,
            r.source_session   = $session_id,
            r.source_messages  = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        ON MATCH SET
            r.last_reinforced  = datetime(),
            r.times_reinforced = coalesce(r.times_reinforced, 1) + 1,
            r.confidence       = $confidence,
            r.source_session   = $session_id,
            r.source_messages  = CASE
                WHEN $message_id IS NULL OR $message_id IN coalesce(r.source_messages, [])
                THEN coalesce(r.source_messages, [])
                ELSE coalesce(r.source_messages, []) + $message_id
            END
        """,
        {
            "user_id":    user_id,
            "top_id":     topic_id,
            "session_id": session_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# memori

async def link_session_to_memory(
    session_id:  str,
    memory_id:   str,
    confidence:  float = 1.0,
    source_message_id: str | None = None,
) -> None:
    """write_memory, backfill, cross-session"""
    await get_client().execute_write(
        """
        MATCH (s:Session {id: $session_id})
        MATCH (m:Memory  {id: $memory_id})
        MERGE (s)-[r:CONTAINS_MEMORY]->(m)
        ON CREATE SET
            r.t_valid         = datetime(),
            r.t_invalid       = null,
            r.confidence      = $confidence,
            r.source_session  = $session_id,
            r.source_messages = CASE WHEN $message_id IS NULL THEN [] ELSE [$message_id] END
        """,
        {
            "session_id": session_id,
            "memory_id":  memory_id,
            "confidence": confidence,
            "message_id": source_message_id,
        },
    )


# maintain bi-temporal

# edge_types = ['edge1', 'edge2'] validate_edge_types(edge_types)
_INVALIDATABLE_EDGES: frozenset[str] = frozenset({
    # skip
    "TRIGGERED_BY",
    "TRIGGERED_EMOTION",
    "ACTIVATED_THOUGHT",
    "ASSOCIATED_WITH",
    "LED_TO_BEHAVIOR",
    # skip klo error
    "EXPERIENCED",
    "FELT",
    "HAS_THOUGHT",
    "HAS_TRIGGER",
    "EXHIBITED",
    "HAS_SUBJECT",
    "HAS_RELATIONSHIP_WITH",       # kept for backward compat
    "HAS_RECURRING_THEME",
    "HAS_MEMORY",
    "COMPLETED_ASSESSMENT",
    # skip klo db
    "HAD_EXPERIENCE",
    "RECORDED_EMOTION",
    "CONTAINS_MEMORY",
    # skip klo error
    "INVOLVES_SUBJECT",
    "INVOLVES_PERSON",             # kept for backward compat
    "RELATED_TO_TOPIC",
})


async def invalidate_edge(
    src_label:  str,
    src_id:     str,
    edge_type:  str,
    dst_label:  str,
    dst_id:     str,
    reason:     str = "user_correction",
) -> int:
    """set_invalid_edge()"""
    if edge_type not in _INVALIDATABLE_EDGES:
        raise ValueError(
            f"edge_type {edge_type!r} not in invalidation allow-list"
        )

    # `limit labels to id chars`
    for arg_name, value in (("src_label", src_label), ("dst_label", dst_label)):
        if not value.isidentifier():
            raise ValueError(f"{arg_name} {value!r} is not a valid Neo4j label")

    records = await get_client().execute_write(
        f"""
        MATCH (src:{src_label} {{id: $src_id}})
              -[r:{edge_type}]->
              (dst:{dst_label} {{id: $dst_id}})
        WHERE r.t_invalid IS NULL
        SET r.t_invalid           = datetime(),
            r.invalidation_reason = $reason
        RETURN count(r) AS invalidated
        """,
        {
            "src_id": src_id,
            "dst_id": dst_id,
            "reason": reason,
        },
    )
    invalidated = records[0]["invalidated"] if records else 0
    if invalidated:
        logger.info(
            "Invalidated %d edge(s): (%s %s)-[:%s]->(%s %s) reason=%s",
            invalidated, src_label, src_id, edge_type, dst_label, dst_id, reason,
        )
    return invalidated

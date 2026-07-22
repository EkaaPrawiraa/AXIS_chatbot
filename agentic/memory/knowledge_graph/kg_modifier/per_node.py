"""update."""

from __future__ import annotations

from typing import Any

from agentic.memory.knowledge_graph.kg_modifier.update_node import update_node_property


# skip

_NOT_GIVEN: Any = object()


def _collect(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not _NOT_GIVEN}


# wraps	end

async def update_emotion(
    emotion_id: str,
    *,
    label:             Any = _NOT_GIVEN,
    intensity:         Any = _NOT_GIVEN,
    valence:           Any = _NOT_GIVEN,
    source_text:       Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
) -> int:
    """patch node's props"""
    return await update_node_property(
        "Emotion",
        emotion_id,
        _collect(
            label=label,
            intensity=intensity,
            valence=valence,
            source_text=source_text,
            sensitivity_level=sensitivity_level,
        ),
    )


async def update_thought(
    thought_id: str,
    *,
    content:           Any = _NOT_GIVEN,
    thought_type:      Any = _NOT_GIVEN,
    distortion:        Any = _NOT_GIVEN,
    believability:     Any = _NOT_GIVEN,
    challenged:        Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
    embedding_synced:  Any = _NOT_GIVEN,
) -> int:
    """patch node"""
    return await update_node_property(
        "Thought",
        thought_id,
        _collect(
            content=content,
            thought_type=thought_type,
            distortion=distortion,
            believability=believability,
            challenged=challenged,
            sensitivity_level=sensitivity_level,
            embedding_synced=embedding_synced,
        ),
    )


async def update_trigger(
    trigger_id: str,
    *,
    category:          Any = _NOT_GIVEN,
    description:       Any = _NOT_GIVEN,
    aliases:           Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
    embedding_synced:  Any = _NOT_GIVEN,
) -> int:
    """patch node's props"""
    return await update_node_property(
        "Trigger",
        trigger_id,
        _collect(
            category=category,
            description=description,
            aliases=aliases,
            sensitivity_level=sensitivity_level,
            embedding_synced=embedding_synced,
        ),
    )


async def update_behavior(
    behavior_id: str,
    *,
    description:       Any = _NOT_GIVEN,
    category:          Any = _NOT_GIVEN,
    adaptive:          Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
) -> int:
    """patch node's props"""
    return await update_node_property(
        "Behavior",
        behavior_id,
        _collect(
            description=description,
            category=category,
            adaptive=adaptive,
            sensitivity_level=sensitivity_level,
        ),
    )


async def update_experience(
    experience_id: str,
    *,
    description:       Any = _NOT_GIVEN,
    valence:           Any = _NOT_GIVEN,
    significance:      Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
    embedding_synced:  Any = _NOT_GIVEN,
) -> int:
    """patch node"""
    return await update_node_property(
        "Experience",
        experience_id,
        _collect(
            description=description,
            valence=valence,
            significance=significance,
            sensitivity_level=sensitivity_level,
            embedding_synced=embedding_synced,
        ),
    )


async def update_subject(
    subject_id: str,
    *,
    name:              Any = _NOT_GIVEN,
    role:              Any = _NOT_GIVEN,
    subject_type:      Any = _NOT_GIVEN,
    sentiment:         Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
) -> int:
    """patch node"""
    return await update_node_property(
        "Subject",
        subject_id,
        _collect(
            name=name,
            role=role,
            subject_type=subject_type,
            sentiment=sentiment,
            sensitivity_level=sensitivity_level,
        ),
    )


async def update_person(
    person_id: str,
    *,
    name:              Any = _NOT_GIVEN,
    role:              Any = _NOT_GIVEN,
    sentiment:         Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
) -> int:
    """`update`"""
    return await update_subject(
        person_id,
        name=name,
        role=role,
        sentiment=sentiment,
        sensitivity_level=sensitivity_level,
    )


async def update_memory(
    memory_id: str,
    *,
    summary:           Any = _NOT_GIVEN,
    importance:        Any = _NOT_GIVEN,
    sensitivity_level: Any = _NOT_GIVEN,
    embedding_synced:  Any = _NOT_GIVEN,
) -> int:
    """patch node's props"""
    return await update_node_property(
        "Memory",
        memory_id,
        _collect(
            summary=summary,
            importance=importance,
            sensitivity_level=sensitivity_level,
            embedding_synced=embedding_synced,
        ),
    )


async def mark_embedding_synced(
    label: str,
    node_id: str,
    *,
    synced: bool = True,
) -> int:
    """skip embeds"""
    return await update_node_property(
        label, node_id, {"embedding_synced": bool(synced)},
    )

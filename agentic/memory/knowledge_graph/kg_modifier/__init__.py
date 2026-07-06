"""agentic/memory/kg_modifier."""

from __future__ import annotations

from agentic.memory.knowledge_graph.kg_modifier.update_node import update_node_property
from agentic.memory.knowledge_graph.kg_modifier.per_node import (
    update_emotion,
    update_thought,
    update_trigger,
    update_behavior,
    update_experience,
    update_person,
    update_memory,
    mark_embedding_synced,
)

__all__ = [
    "update_node_property",
    "update_emotion",
    "update_thought",
    "update_trigger",
    "update_behavior",
    "update_experience",
    "update_person",
    "update_memory",
    "mark_embedding_synced",
]

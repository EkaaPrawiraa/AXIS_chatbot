"""ambil"""

from __future__ import annotations

# ambil
from agentic.memory.knowledge_graph.kg_retriever.schemas import (
    BehaviorInput,
    EmotionInput,
    ExperienceInput,
    MemoryInput,
    SubjectInput,
    PersonInput,     # backward compat alias for SubjectInput
    ThoughtInput,
    TriggerInput,
)

# buat ngbuild
from agentic.memory.knowledge_graph.kg_retriever.relationships import (
    link_emotion_to_thought,
    link_experience_to_emotion,
    link_experience_to_trigger,
    link_thought_emotion_association,
    link_to_behavior,
    link_experience_to_subject,
    link_experience_to_person,   # backward compat alias for link_experience_to_subject
    link_session_to_memory,
    link_to_topic,
    link_user_recurring_theme,
    invalidate_edge,
)

# baca
from agentic.memory.knowledge_graph.kg_retriever.node_readers import (
    read_emotion,
    read_thought,
    read_trigger,
    read_behavior,
    read_experience,
    read_subject,
    read_person,   # backward compat alias for read_subject
    read_memory,
    list_active_thoughts_by_distortion,
    list_active_triggers,
)

# ambil signal
from agentic.memory.knowledge_graph.kg_retriever.signals import (
    fetch_recency,
    fetch_semantic_memories,
    fetch_salient_memories,
    fetch_active_emotions,
    fetch_active_distortions,
    fetch_active_behaviors,
    fetch_recent_experiences,
    fetch_recurring_triggers,
    fetch_recurring_themes,
)

# provenance
from agentic.memory.knowledge_graph.kg_retriever.provenance import (
    facts_for_message,
    nodes_for_message,
)


__all__ = [
    # schemas
    "BehaviorInput",
    "EmotionInput",
    "ExperienceInput",
    "MemoryInput",
    "SubjectInput",
    "PersonInput",   # backward compat alias for SubjectInput
    "ThoughtInput",
    "TriggerInput",
    # skip error
    "link_emotion_to_thought",
    "link_experience_to_emotion",
    "link_experience_to_trigger",
    "link_thought_emotion_association",
    "link_to_behavior",
    "link_experience_to_subject",
    "link_experience_to_person",   # backward compat alias for link_experience_to_subject
    "link_session_to_memory",
    "link_to_topic",
    "link_user_recurring_theme",
    "invalidate_edge",
    # baca data
    "read_emotion",
    "read_thought",
    "read_trigger",
    "read_behavior",
    "read_experience",
    "read_subject",
    "read_person",   # backward compat alias for read_subject
    "read_memory",
    "list_active_thoughts_by_distortion",
    "list_active_triggers",
    # s'lu ngelihar.
    "fetch_recency",
    "fetch_semantic_memories",
    "fetch_salient_memories",
    "fetch_active_emotions",
    "fetch_active_distortions",
    "fetch_active_behaviors",
    "fetch_recent_experiences",
    "fetch_recurring_triggers",
    "fetch_recurring_themes",
    # provenance
    "facts_for_message",
    "nodes_for_message",
]

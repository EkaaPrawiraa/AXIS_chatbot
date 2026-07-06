"""agentic/memory/kg_writer."""

from __future__ import annotations

# Deduplication thresholds.
from agentic.memory.knowledge_graph.kg_writer._common import (
    MERGE_THRESHOLD,
    REVIEW_THRESHOLD,
)

# Input schemas (now hosted by kg_retriever).
from agentic.memory.knowledge_graph.kg_retriever.schemas import (
    BehaviorInput,
    EmotionInput,
    ExperienceInput,
    MemoryInput,
    SubjectInput,
    PersonInput,     # backward compat alias for SubjectInput
    ThoughtInput,
    TopicInput,
    TriggerInput,
)

# Per-node writers.
from agentic.memory.knowledge_graph.kg_writer.behavior_kg          import write_behavior
from agentic.memory.knowledge_graph.kg_writer.emotion_kg            import write_emotion
from agentic.memory.knowledge_graph.kg_writer.experience_kg         import write_experience
from agentic.memory.knowledge_graph.kg_writer.memory_kg             import write_memory
from agentic.memory.knowledge_graph.kg_writer.subject_kg            import write_subject
from agentic.memory.knowledge_graph.kg_writer.person_kg             import write_person  # backward compat alias for write_subject
from agentic.memory.knowledge_graph.kg_writer.thought_kg            import write_thought
from agentic.memory.knowledge_graph.kg_writer.thought_record_writer import write_thought_record
from agentic.memory.knowledge_graph.kg_writer.trigger_kg            import write_trigger
from agentic.memory.knowledge_graph.kg_writer.topic_kg              import write_topic
from agentic.memory.knowledge_graph.kg_writer.user_kg               import ensure_user_node

# Relationship builders (now hosted by kg_retriever).
from agentic.memory.knowledge_graph.kg_retriever.relationships import (
    # CBT chain
    link_emotion_to_thought,
    link_experience_to_emotion,
    link_experience_to_trigger,
    link_thought_emotion_association,
    link_to_behavior,
    # Contextual
    link_experience_to_subject,
    link_experience_to_person,   # backward compat alias for link_experience_to_subject
    link_session_to_memory,
    link_to_topic,
    link_user_recurring_theme,
    # Bi-temporal maintenance
    invalidate_edge,
)

# Algorithmic operations (now hosted by kg_algorithm).
from agentic.memory.knowledge_graph.kg_algorithm.supersession import supersede_thought
from agentic.memory.knowledge_graph.kg_algorithm.decay        import run_memory_decay
from agentic.memory.knowledge_graph.kg_algorithm.lifecycle import (
    deactivate_trigger,
    reappraise_experience,
    replace_behavior,
)

# Lifecycle (now split across kg_deleter / kg_modifier).
from agentic.memory.knowledge_graph.kg_deleter.soft_delete  import invalidate_message
from agentic.memory.knowledge_graph.kg_deleter.hard_delete  import purge_message, purge_user
from agentic.memory.knowledge_graph.kg_modifier.update_node import update_node_property


__all__ = [
    # thresholds
    "MERGE_THRESHOLD",
    "REVIEW_THRESHOLD",
    # schemas
    "BehaviorInput",
    "EmotionInput",
    "ExperienceInput",
    "MemoryInput",
    "SubjectInput",
    "PersonInput",   # backward compat alias for SubjectInput
    "ThoughtInput",
    "TopicInput",
    "TriggerInput",
    # writers
    "write_behavior",
    "write_emotion",
    "write_experience",
    "write_thought_record",
    "write_memory",
    "write_subject",
    "write_person",  # backward compat alias for write_subject
    "write_thought",
    "write_trigger",
    "write_topic",
    "ensure_user_node",
    # relationship builders -- CBT chain
    "link_emotion_to_thought",
    "link_experience_to_emotion",
    "link_experience_to_trigger",
    "link_thought_emotion_association",
    "link_to_behavior",
    # relationship builders -- contextual
    "link_experience_to_subject",
    "link_experience_to_person",   # backward compat alias for link_experience_to_subject
    "link_session_to_memory",
    "link_to_topic",
    "link_user_recurring_theme",
    # bi-temporal maintenance
    "invalidate_edge",
    # supersession & decay (re-exported from kg_algorithm)
    "supersede_thought",
    "run_memory_decay",
    "deactivate_trigger",
    "reappraise_experience",
    "replace_behavior",
    # lifecycle (re-exported from kg_deleter / kg_modifier)
    "invalidate_message",
    "purge_message",
    "purge_user",
    "update_node_property",
]

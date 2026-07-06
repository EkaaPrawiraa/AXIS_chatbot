"""Input dataclasses for every AI-coupled writer in the kg_writer package."""

from __future__ import annotations

from dataclasses import dataclass


# Emotion  (CBT hot-cross-bun: feelings)

@dataclass
class EmotionInput:
    """
    Discrete emotional event. Not deduplicated -- each utterance-level
    emotion is time-stamped and preserved as its own node.

    Schema notes (post 2026-05 cleanup):
        - ``intensity`` and ``valence`` are the only PAD-style numerics
          retained because they have live readers (context_builder
          surfacing + DistressSnapshot aggregation in assessment_repo).
        - ``arousal`` and ``dominance`` were dropped together with the
          per-turn emotion_detection node; no downstream code consumed
          them.
    """
    label:        str              # e.g. "anxious", "sad", "grateful"
    intensity:    float            # [0, 1] strength of the felt emotion
    valence:      float            # [-1, 1] pleasure-displeasure axis
    source_text:  str              # original user utterance
    user_id:      str
    session_id:   str
    confidence:        float = 0.85
    sensitivity_level: str   = "normal"
    source_message_id: str | None = None


# Thought  (CBT hot-cross-bun: thoughts / cognitions)

@dataclass
class ThoughtInput:
    """
    An automatic thought, intermediate belief, or core belief.

    When deduplicated, the existing node's believability is averaged with
    the new value and ``challenged`` resets to false.
    """
    content:         str
    thought_type:    str              # "automatic" | "core_belief" | "intermediate"
    distortion:      str | None       # "catastrophizing" | "mind_reading" | "all_or_nothing" | "fortune_telling" | "emotional_reasoning" | "should_statements" | "labeling" | "magnification" | "personalization" | "overgeneralization" | None
    believability:   float            # [0, 1]
    user_id:         str
    session_id:      str
    embedding:       list[float] | None = None
    confidence:        float = 0.80
    sensitivity_level: str   = "normal"
    source_message_id: str | None = None


# Trigger  (CBT hot-cross-bun: antecedent)

@dataclass
class TriggerInput:
    """
    A recurring antecedent -- what set off the experience.
    Deduplicated by (user, category, description prefix) on the fast
    path; cosine similarity in pgvector on the slow path (DevNotes
    v1.3, Section 1.3 marks Trigger as embeddable for entity dedup
    across phrasings such as "exam stress" / "academic anxiety" /
    "test fear").

    ``aliases`` carries the alternative phrasings collected during
    deduplication. Per real KG schema, the canonical Trigger node
    keeps the aliases list.

    ``embedding`` is the dense vector for the description. Forwarded
    to ``trigger_embeddings`` in pgvector by the writer; never stored
    on the Neo4j node itself.
    """
    category:     str                  # "academic" | "social" | "family" | "work" | ...
    description:  str
    significance: float                # [0, 1] write-gate + pgvector importance
    user_id:      str
    session_id:   str
    aliases:      list[str] | None = None
    embedding:    list[float] | None = None
    confidence:        float = 0.85
    sensitivity_level: str   = "normal"
    source_message_id: str | None = None


# Behavior  (CBT hot-cross-bun: behavior)

@dataclass
class BehaviorInput:
    """
    Observable action the user took. Marked adaptive / maladaptive so the
    recommendation engine can surface healthier alternatives for the
    maladaptive ones.
    """
    description:  str
    category:     str                  # "avoidance" | "rumination" | "exercise" | ...
    adaptive:     bool
    significance: float                # [0, 1] write-gate + pgvector importance
    user_id:      str
    session_id:   str
    confidence:        float = 0.80
    sensitivity_level: str   = "normal"
    embedding:         list[float] | None = None
    source_message_id: str | None = None


# Experience  (CBT hot-cross-bun: situation)

@dataclass
class ExperienceInput:
    """
    A concrete situation the user lived through -- the anchor of the
    CBT chain. Deduplicated via cosine similarity on ``embedding``.
    """
    description:   str
    occurred_at:   str                 # ISO datetime string
    extracted_at:  str                 # ISO datetime string
    valence:       float               # [-1, 1]
    significance:  float               # [0, 1]
    user_id:       str
    session_id:    str
    embedding:     list[float] | None = None
    confidence:        float = 0.85
    sensitivity_level: str   = "normal"
    source_message_id: str | None = None


# Subject  (social/entity graph — replaces :Person node)

@dataclass
class SubjectInput:
    """
    A subject (person, pet, object, place, or other entity) mentioned by the
    user. MERGE-upserted by (user_id, name).
    Sentiment is a running average; mention_count increments on match.

    The User edge is HAS_SUBJECT (per updated KG schema); ``relationship_quality``
    is carried on that edge as a coarse summary of the bond.
    Allowed values: "supportive", "complicated", "negative", "neutral".
    """
    name:                str
    role:                str   # "parent" | "friend" | "partner" | "professor" | ...
    sentiment:           float                # [-1, 1]
    user_id:             str
    session_id:          str
    subject_type:        str  = "person"      # "person" | "pet" | "object" | "place" | "other"
    relationship_quality: str  = "neutral"    # supportive | complicated | negative | neutral
    confidence:          float = 0.80
    source_message_id:   str | None = None


PersonInput = SubjectInput  # backward compat alias


# Memory  (compressed post-session summary)

@dataclass
class MemoryInput:
    """
    Compressed session summary written once per session from
    session_end.py. Memories decay: importance halves after 60 days
    without access, active flips to false after 180 days.
    """
    summary:     str
    importance:  float                  # [0, 1]
    user_id:     str
    session_id:  str
    embedding:         list[float] | None = None
    sensitivity_level: str = "normal"
    source_message_id: str | None = None


# Topic  (recurring theme detected in conversation)

@dataclass
class TopicInput:
    """
    A high-abstraction recurring theme extracted from a session turn.
    Topic nodes are MERGED by name (case-insensitive), so the same
    conceptual topic accumulates frequency across sessions rather than
    spawning duplicate nodes.

    Owner: Python (extraction from LLM-classified turns).
    Go also owns a UpsertTopic endpoint for its own writes; both target
    the same Neo4j node shape and use the same MERGE-by-name pattern.
    """
    name:       str           # e.g. "academic-stress", "relationship-conflict"
    category:   str           # "academic"|"social"|"family"|"career"|"health"|
                              # "financial"|"identity"|"mental_health"|"other"
    sentiment:  float         # [-1, 1] average sentiment in the turn
    user_id:    str
    session_id: str
    source_message_id: str | None = None

"""`for writer in kg_writer: writer.input_dataclass()`"""

from __future__ import annotations

from dataclasses import dataclass


# feel

@dataclass
class EmotionInput:
    """discrete"""
    label:        str              # e.g. "anxious", "sad", "grateful"
    intensity:    float            # [0, 1] strength of the felt emotion
    valence:      float            # [-1, 1] pleasure-displeasure axis
    source_text:  str              # original user utterance
    user_id:      str
    session_id:   str
    confidence:        float = 0.85
    sensitivity_level: str   = "normal"
    source_message_id: str | None = None


# skip

@dataclass
class ThoughtInput:
    """reset belis"""
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


# ambil data

@dataclass
class TriggerInput:
    """cosine_sim"""
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


# hot-cross-bun

@dataclass
class BehaviorInput:
    """adapt or avoid"""
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


# situasi

@dataclass
class ExperienceInput:
    """cos_sim"""
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


# skip error

@dataclass
class SubjectInput:
    """merge, upsert, sentiment, match, count, update, user, edge, HAS_SUBJECT, relationship_quality, supportive, complicated, negative, neutral"""
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


# post-sessions

@dataclass
class MemoryInput:
    """sum, decay, imp, acc, time"""
    summary:     str
    importance:  float                  # [0, 1]
    user_id:     str
    session_id:  str
    embedding:         list[float] | None = None
    sensitivity_level: str = "normal"
    source_message_id: str | None = None


# skip

@dataclass
class TopicInput:
    """merge it"""
    name:       str           # e.g. "academic-stress", "relationship-conflict"
    category:   str           # "academic"|"social"|"family"|"career"|"health"|
                              # "financial"|"identity"|"mental_health"|"other"
    sentiment:  float         # [-1, 1] average sentiment in the turn
    user_id:    str
    session_id: str
    source_message_id: str | None = None

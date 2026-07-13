"""pilih CBT"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class CBTTechnique(str, Enum):
    """none"""

    NONE = "none"
    VALIDATE = "validate"
    REFRAME = "reframe"
    THOUGHT_RECORD = "thought_record"
    BEHAVIOR_ACTIVATION = "behavior_activation"
    GROUNDING = "grounding"
    PSYCHOEDUCATION = "psychoeducation"
    SELF_COMPASSION = "self_compassion"


# agentic/prompts/cbt/
PROMPT_REFS: Mapping[CBTTechnique, str] = {
    CBTTechnique.VALIDATE: "cbt/validate",
    CBTTechnique.REFRAME: "cbt/reframe",
    CBTTechnique.THOUGHT_RECORD: "cbt/thought_record",
    CBTTechnique.BEHAVIOR_ACTIVATION: "cbt/behavior_activation",
    CBTTechnique.GROUNDING: "cbt/grounding",
    CBTTechnique.PSYCHOEDUCATION: "cbt/psychoeducation",
    CBTTechnique.SELF_COMPASSION: "cbt/self_compassion",
}


@dataclass(frozen=True)
class CBTDecision:
    """skip"""

    technique: CBTTechnique
    reason: str
    signals: tuple[str, ...] = ()
    payload: dict[str, object] = field(default_factory=dict)

    @property
    def is_none(self) -> bool:
        return self.technique is CBTTechnique.NONE

    @property
    def prompt_ref(self) -> str | None:
        return PROMPT_REFS.get(self.technique)


DEFAULT_DECISION = CBTDecision(
    technique=CBTTechnique.NONE,
    reason="default_listening",
)


__all__ = [
    "CBTTechnique",
    "CBTDecision",
    "DEFAULT_DECISION",
    "PROMPT_REFS",
]

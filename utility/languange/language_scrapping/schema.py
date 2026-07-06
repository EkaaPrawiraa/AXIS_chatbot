"""Schema and validation for linguistic corpus entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Category = Literal["L1", "L2", "L3", "L4"]
Language = Literal["id", "en", "en-borrowed", "mix"]
Register = Literal["formal", "informal", "slang", "mixed"]
EmotionalWeight = Literal["low", "medium", "high"]


REQUIRED_FIELDS = (
    "term",
    "category",
    "language",
    "register",
    "definition_id",
    "definition_en",
    "usage_examples",
    "emotional_weight",
    "distress_signal",
    "escalation_flag",
    "clinical_note",
    "source",
    "validated",
    "added_date",
)


@dataclass(frozen=True)
class Entry:
    term: str
    category: Category
    language: Language
    register: Register
    definition_id: str
    definition_en: str
    usage_examples: list[str] = field(default_factory=list)
    emotional_weight: EmotionalWeight = "medium"
    distress_signal: bool = False
    escalation_flag: bool = False
    clinical_note: str = ""
    source: str = ""
    validated: bool = False
    added_date: str = ""

    def to_dict(self) -> dict:
        return {
            "term": self.term,
            "category": self.category,
            "language": self.language,
            "register": self.register,
            "definition_id": self.definition_id,
            "definition_en": self.definition_en,
            "usage_examples": list(self.usage_examples),
            "emotional_weight": self.emotional_weight,
            "distress_signal": bool(self.distress_signal),
            "escalation_flag": bool(self.escalation_flag),
            "clinical_note": self.clinical_note,
            "source": self.source,
            "validated": bool(self.validated),
            "added_date": self.added_date,
        }

    @staticmethod
    def from_dict(payload: dict) -> "Entry":
        missing = [k for k in REQUIRED_FIELDS if k not in payload]
        if missing:
            raise ValueError(f"missing fields: {missing}")
        return Entry(
            term=str(payload["term"]).strip(),
            category=str(payload["category"]).strip(),
            language=str(payload["language"]).strip(),
            register=str(payload["register"]).strip(),
            definition_id=str(payload["definition_id"]).strip(),
            definition_en=str(payload["definition_en"]).strip(),
            usage_examples=list(payload.get("usage_examples") or []),
            emotional_weight=str(payload["emotional_weight"]).strip(),
            distress_signal=bool(payload["distress_signal"]),
            escalation_flag=bool(payload["escalation_flag"]),
            clinical_note=str(payload["clinical_note"]).strip(),
            source=str(payload["source"]).strip(),
            validated=bool(payload["validated"]),
            added_date=str(payload["added_date"]).strip(),
        )


def validate_entry(entry: Entry) -> list[str]:
    errors: list[str] = []
    if not entry.term:
        errors.append("term is empty")
    if entry.category not in ("L1", "L2", "L3", "L4"):
        errors.append(f"invalid category: {entry.category}")
    if entry.language not in ("id", "en", "en-borrowed", "mix"):
        errors.append(f"invalid language: {entry.language}")
    if entry.register not in ("formal", "informal", "slang", "mixed"):
        errors.append(f"invalid register: {entry.register}")
    if entry.emotional_weight not in ("low", "medium", "high"):
        errors.append(f"invalid emotional_weight: {entry.emotional_weight}")
    if not entry.definition_id:
        errors.append("definition_id is empty")
    if not entry.usage_examples:
        errors.append("usage_examples is empty")
    if entry.escalation_flag and not entry.distress_signal:
        errors.append("escalation_flag true but distress_signal false")
    return errors

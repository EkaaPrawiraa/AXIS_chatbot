"""adapt Beck 1979 & Beck 2011"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from agentic.agent.cbt.distortions import DISTORTIONS, Distortion


class ThoughtRecordStep(str, Enum):
    CATCH_THOUGHT = "catch_thought"
    LABEL_DISTORTION = "label_distortion"
    EVIDENCE_FOR = "evidence_for"
    EVIDENCE_AGAINST = "evidence_against"
    BALANCED_THOUGHT = "balanced_thought"
    DONE = "done"


_NEXT_STEP: dict[ThoughtRecordStep, ThoughtRecordStep] = {
    ThoughtRecordStep.CATCH_THOUGHT: ThoughtRecordStep.LABEL_DISTORTION,
    ThoughtRecordStep.LABEL_DISTORTION: ThoughtRecordStep.EVIDENCE_FOR,
    ThoughtRecordStep.EVIDENCE_FOR: ThoughtRecordStep.EVIDENCE_AGAINST,
    ThoughtRecordStep.EVIDENCE_AGAINST: ThoughtRecordStep.BALANCED_THOUGHT,
    ThoughtRecordStep.BALANCED_THOUGHT: ThoughtRecordStep.DONE,
    ThoughtRecordStep.DONE: ThoughtRecordStep.DONE,
}


@dataclass
class ThoughtRecordSubState:
    """buat nyimpen sub-state"""

    step: ThoughtRecordStep = ThoughtRecordStep.CATCH_THOUGHT
    thought: str | None = None
    distortion: str | None = None  # canonical name from DISTORTIONS
    evidence_for: str | None = None
    evidence_against: str | None = None
    balanced: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step.value,
            "thought": self.thought,
            "distortion": self.distortion,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "balanced": self.balanced,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ThoughtRecordSubState":
        if not data:
            return cls()
        try:
            step = ThoughtRecordStep(data.get("step", "catch_thought"))
        except ValueError:
            step = ThoughtRecordStep.CATCH_THOUGHT
        return cls(
            step=step,
            thought=data.get("thought"),
            distortion=data.get("distortion"),
            evidence_for=data.get("evidence_for"),
            evidence_against=data.get("evidence_against"),
            balanced=data.get("balanced"),
        )



def _prompt_catch(language: str) -> str:
    if language == "id":
        return (
            "Bisa kamu coba tuliskan satu kalimat pikiran yang muncul "
            "paling kuat saat itu? Tulis dalam kata-katamu sendiri."
        )
    return (
        "Could you write one sentence that captures the thought that "
        "stood out the most? Use your own words."
    )


def _prompt_distortion(language: str, hinted: Distortion | None) -> str:
    if hinted is not None:
        label = hinted.label_id if language == "id" else hinted.label_en
        if language == "id":
            return (
                f"Aku menangkap pola yang mirip {label}. Apakah itu terasa "
                "tepat, atau menurutmu pola lain yang lebih cocok?"
            )
        return (
            f"I noticed a pattern that looks like {label}. Does that "
            "feel right, or does another pattern fit better?"
        )
    if language == "id":
        return (
            "Pola pikir mana yang menurutmu paling pas: hitam-putih, "
            "meramal, membaca pikiran, atau yang lain?"
        )
    return (
        "Which pattern feels closest: all-or-nothing, fortune telling, "
        "mind reading, or something else?"
    )


def _prompt_evidence_for(language: str) -> str:
    if language == "id":
        return (
            "Apa fakta atau bukti yang membuat pikiran itu terasa benar? "
            "Boleh sebut satu atau dua hal."
        )
    return (
        "What facts make that thought feel true? One or two are enough."
    )


def _prompt_evidence_against(language: str) -> str:
    if language == "id":
        return (
            "Sekarang coba balik. Apa fakta atau bukti yang justru "
            "menentang pikiran tadi?"
        )
    return "Now flip it. What facts go against that thought?"


def _prompt_balanced(language: str, distortion: Distortion | None) -> str:
    if distortion is not None:
        return distortion.socratic(language)
    if language == "id":
        return (
            "Kalau menggabungkan dua sisi tadi, kira-kira pikiran yang "
            "lebih seimbang tentang situasi ini bagaimana?"
        )
    return (
        "Putting both sides together, what would a more balanced thought "
        "about the situation sound like?"
    )


def _prompt_done(sub: ThoughtRecordSubState, language: str) -> str:
    if language == "id":
        return (
            "Itu hasil yang bagus. Pikiran yang lebih seimbang tadi bisa "
            "kita simpan, dan kapan-kapan kalau pola yang sama muncul, "
            "kita bisa balik ke catatan ini."
        )
    return (
        "That is solid work. We can keep that balanced thought, and if "
        "the same pattern shows up later we can return to this note."
    )



@dataclass
class ThoughtRecordTurn:
    """out"""

    bot_prompt: str
    next_state: ThoughtRecordSubState
    completed: bool


class ThoughtRecordMachine:
    """machine = ThoughtRecordMachine() turn = machine.step(     sub_state=ThoughtRecordSubState(),     user_reply="",     language="id",     hinted_distortion=DISTORTIONS["catastrophizing"], )"""

    async def step(
        self,
        *,
        sub_state: ThoughtRecordSubState,
        user_reply: str,
        language: str = "id",
        hinted_distortion: Distortion | None = None,
        llm: Any | None = None,
    ) -> ThoughtRecordTurn:
        # buat nyimpan reply
        if user_reply.strip():
            self._record_reply(sub_state, user_reply.strip(), hinted_distortion)
            sub_state.step = _NEXT_STEP[sub_state.step]

        return self._emit(sub_state, language, hinted_distortion)

    def _record_reply(
        self,
        sub: ThoughtRecordSubState,
        reply: str,
        hinted_distortion: Distortion | None,
    ) -> None:
        if sub.step == ThoughtRecordStep.CATCH_THOUGHT:
            sub.thought = reply
        elif sub.step == ThoughtRecordStep.LABEL_DISTORTION:
            normalized = reply.lower().strip()
            if normalized in DISTORTIONS:
                sub.distortion = normalized
            elif hinted_distortion is not None and normalized in (
                "ya", "iya", "yes", "yep", "betul", "right",
            ):
                sub.distortion = hinted_distortion.name
            else:
                # search
                match = next(
                    (n for n in DISTORTIONS if n in normalized),
                    None,
                )
                sub.distortion = match
        elif sub.step == ThoughtRecordStep.EVIDENCE_FOR:
            sub.evidence_for = reply
        elif sub.step == ThoughtRecordStep.EVIDENCE_AGAINST:
            sub.evidence_against = reply
        elif sub.step == ThoughtRecordStep.BALANCED_THOUGHT:
            sub.balanced = reply

    def _emit(
        self,
        sub: ThoughtRecordSubState,
        language: str,
        hinted_distortion: Distortion | None,
    ) -> ThoughtRecordTurn:
        distortion_obj = (
            DISTORTIONS.get(sub.distortion) if sub.distortion else hinted_distortion
        )

        if sub.step == ThoughtRecordStep.CATCH_THOUGHT:
            return ThoughtRecordTurn(
                bot_prompt=_prompt_catch(language),
                next_state=sub,
                completed=False,
            )
        if sub.step == ThoughtRecordStep.LABEL_DISTORTION:
            return ThoughtRecordTurn(
                bot_prompt=_prompt_distortion(language, hinted_distortion),
                next_state=sub,
                completed=False,
            )
        if sub.step == ThoughtRecordStep.EVIDENCE_FOR:
            return ThoughtRecordTurn(
                bot_prompt=_prompt_evidence_for(language),
                next_state=sub,
                completed=False,
            )
        if sub.step == ThoughtRecordStep.EVIDENCE_AGAINST:
            return ThoughtRecordTurn(
                bot_prompt=_prompt_evidence_against(language),
                next_state=sub,
                completed=False,
            )
        if sub.step == ThoughtRecordStep.BALANCED_THOUGHT:
            return ThoughtRecordTurn(
                bot_prompt=_prompt_balanced(language, distortion_obj),
                next_state=sub,
                completed=False,
            )
        # skip
        return ThoughtRecordTurn(
            bot_prompt=_prompt_done(sub, language),
            next_state=sub,
            completed=True,
        )


__all__ = [
    "ThoughtRecordStep",
    "ThoughtRecordSubState",
    "ThoughtRecordTurn",
    "ThoughtRecordMachine",
]

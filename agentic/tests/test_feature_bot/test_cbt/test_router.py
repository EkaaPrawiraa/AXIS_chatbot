"""test cbt decisions"""

from __future__ import annotations

from typing import Any

import pytest

from agentic.agent.cbt.router import route
from agentic.agent.cbt.techniques import CBTTechnique


def _state(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "user_id": "u",
        "session_id": "s",
        "current_message": "",
        "phq9_state": {"phase": "idle"},
        "cbt_state": {},
        "kg_context": "",
        "resolved_language": "id",
    }
    base.update(kw)
    return base


class TestSafety:
    def test_crisis_flag_blocks(self) -> None:
        d = route(_state(safety_flag="crisis"))
        assert d.technique is CBTTechnique.NONE
        assert d.reason == "safety_flag_blocked"

    def test_phq9_active_blocks(self) -> None:
        d = route(_state(phq9_state={"phase": "in_progress"}))
        assert d.technique is CBTTechnique.NONE
        assert d.reason == "phq9_active"


# per-turn PAD" & "emotion_detection" gone. LLM handles acuteness now. Docs updated.


class TestThoughtRecordResume:
    def test_in_progress_thought_record_resumes(self) -> None:
        d = route(_state(
            current_message="apapun",
            cbt_state={"thought_record_active": True},
        ))
        assert d.technique is CBTTechnique.THOUGHT_RECORD


class TestDistortion:
    def test_active_distortion_offers_reframe(self) -> None:
        d = route(_state(current_message="aku selalu gagal"))
        assert d.technique is CBTTechnique.REFRAME
        assert d.payload.get("distortion") == "overgeneralization"

    def test_explicit_reframe_request_with_distortion_escalates(self) -> None:
        d = route(_state(
            current_message="aku pasti gagal final ini, bantu reframe dong",
        ))
        assert d.technique is CBTTechnique.THOUGHT_RECORD
        assert d.payload.get("distortion")

    def test_continuation_message_can_use_prior_distortion(self) -> None:
        d = route(_state(
            current_message="iya",
            cbt_state={
                "last_directive": {
                    "technique": "reframe",
                    "reason": "active_distortion",
                    "signals": ["distortion"],
                    "payload": {"distortion": "catastrophizing"},
                }
            },
        ))
        assert d.technique is CBTTechnique.REFRAME
        assert d.reason == "context_distortion"
        assert d.payload.get("distortion") == "catastrophizing"

    def test_topic_shift_does_not_use_prior_distortion(self) -> None:
        d = route(_state(
            current_message="ngomong-ngomong aku makan nasi goreng",
            cbt_state={
                "last_directive": {
                    "technique": "reframe",
                    "reason": "active_distortion",
                    "signals": ["distortion"],
                    "payload": {"distortion": "catastrophizing"},
                }
            },
        ))
        # NONE
        assert d.technique is CBTTechnique.NONE


class TestBehaviorActivation:
    def test_avoidance_low_valence(self) -> None:
        d = route(_state(
            current_message="seharian tidur seharian, ga keluar kamar",
        ))
        # avoidance cue; trigger msg; support tech; fire.
        assert d.technique in (
            CBTTechnique.BEHAVIOR_ACTIVATION,
            CBTTechnique.REFRAME,
        )

    def test_pure_avoidance_no_distortion_triggers_ba(self) -> None:
        d = route(_state(
            current_message="ga keluar kamar dan ga balas chat",
        ))
        assert d.technique is CBTTechnique.BEHAVIOR_ACTIVATION


class TestSelfCompassion:
    def test_self_criticism_cue_triggers_compassion(self) -> None:
        d = route(_state(
            current_message="aku payah banget jadi orang",
        ))
        # payah" wins.
        assert d.technique in (
            CBTTechnique.SELF_COMPASSION,
            CBTTechnique.REFRAME,
        )


class TestPsychoeducation:
    def test_definition_question_triggers_psychoed(self) -> None:
        d = route(_state(current_message="apa sih yang dimaksud distortion?"))
        assert d.technique is CBTTechnique.PSYCHOEDUCATION


class TestDefault:
    def test_casual_greeting_is_none_not_validate(self) -> None:
        """NONE"""
        d = route(_state(current_message="halo, hari ini gimana"))
        assert d.technique is CBTTechnique.NONE
        assert d.reason == "casual_no_emotional_content"

    def test_message_with_mild_feeling_still_validates(self) -> None:
        d = route(_state(current_message="capek banget hari ini abis kelas"))
        assert d.technique is CBTTechnique.VALIDATE
        assert d.reason == "default_validate"

    def test_distress_term_from_linguistic_signals_forces_validate(self) -> None:
        """validate via linguistic_signals.distress_terms"""
        d = route(_state(
            current_message="gakuat rasanya minggu ini",
            linguistic_signals={"distress_terms": ["gakuat"]},
        ))
        assert d.technique is CBTTechnique.VALIDATE


class TestOptOutCooldown:
    def test_repeat_offer_after_decline_falls_back_to_validate(self) -> None:
        d = route(_state(
            current_message="aku selalu gagal",
            cbt_state={
                "last_offered": "reframe",
                "declined_last_offer": True,
            },
        ))
        # `skip demote`
        assert d.technique is CBTTechnique.VALIDATE
        assert d.reason == "opt_out_cooldown"

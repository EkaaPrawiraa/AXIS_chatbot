"""test cbt decisions"""

from __future__ import annotations

from typing import Any

import pytest

import agentic.agent.cbt.router as router_module
from agentic.agent.cbt.judge import JudgeOutcome
from agentic.agent.cbt.router import extract_signals, route, route_with_llm
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


# docs updated


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

    def test_neutral_message_with_distortion_cue_is_not_reframed(self) -> None:
        """skip reframe"""
        d = route(_state(
            current_message=(
                "kelas besok wajib hadir jam 8, terus abis itu aku mau makan "
                "bakso, aku emang selalu suka bakso"
            ),
        ))
        assert d.technique is CBTTechnique.NONE
        assert d.reason == "casual_no_emotional_content"

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
        # skip klo error
        assert d.technique is CBTTechnique.NONE


class TestBehaviorActivation:
    def test_avoidance_low_valence(self) -> None:
        d = route(_state(
            current_message="seharian tidur seharian, ga keluar kamar",
        ))
        # avoid; trigger; tech; fire.
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
        # payah wins
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
        """skip klo error"""
        d = route(_state(current_message="halo, hari ini gimana"))
        assert d.technique is CBTTechnique.NONE
        assert d.reason == "casual_no_emotional_content"

    def test_message_with_mild_feeling_still_validates(self) -> None:
        d = route(_state(current_message="capek banget hari ini abis kelas"))
        assert d.technique is CBTTechnique.VALIDATE
        assert d.reason == "default_validate"

    def test_distress_term_from_linguistic_signals_forces_validate(self) -> None:
        """validate via distress_terms"""
        d = route(_state(
            current_message="gakuat rasanya minggu ini",
            linguistic_signals={"distress_terms": ["gakuat"]},
        ))
        assert d.technique is CBTTechnique.VALIDATE


class TestJudgeRouting:
    """warm-up, turn, gate, confidence."""

    @staticmethod
    def _stub_outcome(
        technique: CBTTechnique, confidence: float
    ) -> JudgeOutcome:
        return JudgeOutcome(
            technique=technique,
            reason="judge_decision",
            distortion=None,
            confidence=confidence,
            rationale="stubbed for test",
        )

    @pytest.mark.asyncio
    async def test_grounding_blocked_before_warmup_turns_even_at_high_confidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """regression: high-conf call for GROUNDING must wait CBT_MIN_TURN_BEFORE_OFFER."""
        async def fake_judge(state, *, llm=None):
            return self._stub_outcome(CBTTechnique.GROUNDING, confidence=0.95)

        monkeypatch.setattr(router_module, "judge_technique", fake_judge)
        state = _state(
            current_message="makin deket deadline bikin deg-degan parah",
            session_turn=1,
        )
        d = await route_with_llm(state, judge_llm=object())
        assert d.technique is not CBTTechnique.GROUNDING

    @pytest.mark.asyncio
    async def test_grounding_allowed_after_warmup_turns_at_high_confidence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def fake_judge(state, *, llm=None):
            return self._stub_outcome(CBTTechnique.GROUNDING, confidence=0.95)

        monkeypatch.setattr(router_module, "judge_technique", fake_judge)
        state = _state(
            current_message="deg-degan parah, jantung berdebar kenceng banget",
            session_turn=router_module.CBT_MIN_TURN_BEFORE_OFFER,
        )
        d = await route_with_llm(state, judge_llm=object())
        assert d.technique is CBTTechnique.GROUNDING

    @pytest.mark.asyncio
    async def test_grounding_at_weak_confidence_falls_back_to_rules(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """clear old 0.4, dont clear new 0.7."""
        async def fake_judge(state, *, llm=None):
            return self._stub_outcome(CBTTechnique.GROUNDING, confidence=0.5)

        monkeypatch.setattr(router_module, "judge_technique", fake_judge)
        state = _state(
            current_message="capek banget hari ini abis kelas",
            session_turn=router_module.CBT_MIN_TURN_BEFORE_OFFER,
        )
        d = await route_with_llm(state, judge_llm=object())
        assert d.technique is not CBTTechnique.GROUNDING


class TestOptOutCooldown:
    def test_repeat_offer_after_decline_falls_back_to_validate(self) -> None:
        d = route(_state(
            current_message="aku selalu gagal",
            cbt_state={
                "last_offered": "reframe",
                "declined_last_offer": True,
            },
        ))
        # skip
        assert d.technique is CBTTechnique.VALIDATE
        assert d.reason == "opt_out_cooldown"


class TestGroundingFollowup:
    """turn right after grounding should revisit a distortion left unaddressed (Lampiran N.3 finding)"""

    def _grounding_last_directive(self, distortion: str | None = "catastrophizing") -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if distortion is not None:
            payload["distortion"] = distortion
        return {
            "technique": "grounding",
            "reason": "acute_affect",
            "signals": ["llm_judge"],
            "payload": payload,
        }

    def test_followup_offers_reframe_with_prior_distortion(self) -> None:
        d = route(_state(
            current_message="masih kepikiran soal itu, takut hasilnya jelek banget",
            cbt_state={"last_directive": self._grounding_last_directive("catastrophizing")},
        ))
        assert d.technique is CBTTechnique.REFRAME
        assert d.reason == "grounding_followup_distortion"
        assert d.payload["distortion"] == "catastrophizing"
        assert "grounding_followup" in d.signals

    def test_followup_skipped_when_message_has_no_emotional_content(self) -> None:
        d = route(_state(
            current_message="btw jam berapa kelas besok ya",
            cbt_state={"last_directive": self._grounding_last_directive("catastrophizing")},
        ))
        assert d.reason != "grounding_followup_distortion"

    def test_followup_skipped_when_no_distortion_was_recorded(self) -> None:
        state = _state(
            current_message="masih cemas dikit tapi mendingan sekarang",
            cbt_state={"last_directive": self._grounding_last_directive(None)},
        )
        assert extract_signals(state).has_emotional_content is True  # sanity: test isolates the right variable
        d = route(state)
        assert d.reason != "grounding_followup_distortion"

    def test_followup_skipped_when_last_technique_was_not_grounding(self) -> None:
        d = route(_state(
            current_message="masih kepikiran soal itu, takut hasilnya jelek banget",
            cbt_state={"last_directive": {
                "technique": "validate", "reason": "default_validate",
                "signals": [], "payload": {},
            }},
        ))
        assert d.reason != "grounding_followup_distortion"

    def test_followup_fires_only_once_across_two_turns(self) -> None:
        state = _state(
            current_message="masih kepikiran soal itu, takut hasilnya jelek banget",
            cbt_state={"last_directive": self._grounding_last_directive("catastrophizing")},
        )
        first = route(state)
        assert first.reason == "grounding_followup_distortion"

        # simulate dialogue_policy_node committing the new directive, then a 2nd turn
        next_state = _state(
            current_message="iya masih mikirin itu terus",
            cbt_state={"last_directive": {
                "technique": first.technique.value,
                "reason": first.reason,
                "signals": list(first.signals),
                "payload": dict(first.payload),
            }},
        )
        second = route(next_state)
        assert second.reason != "grounding_followup_distortion"

    @pytest.mark.asyncio
    async def test_followup_takes_priority_over_llm_judge(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """followup must fire even if the judge would suggest something else"""
        async def fake_judge(state, *, llm=None):
            return JudgeOutcome(
                technique=CBTTechnique.VALIDATE,
                reason="judge_decision",
                distortion=None,
                confidence=0.95,
                rationale="stubbed for test",
            )

        monkeypatch.setattr(router_module, "judge_technique", fake_judge)
        state = _state(
            current_message="masih kepikiran soal itu, takut hasilnya jelek banget",
            cbt_state={"last_directive": self._grounding_last_directive("catastrophizing")},
            session_turn=router_module.CBT_MIN_TURN_BEFORE_OFFER,
        )
        d = await route_with_llm(state, judge_llm=object())
        assert d.technique is CBTTechnique.REFRAME
        assert d.reason == "grounding_followup_distortion"

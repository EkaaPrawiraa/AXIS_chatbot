"""fake, PHQ-9, suite, Postgres, run, without, suite, Postgres, without, Postgres, without, Postgres, without, Postgres, without, Postgres, without, Postgres, without, Postgres, without, Postgres, without, Postgres"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pytest

from agentic.assessment.phq9 import PHQ9Severity
from agentic.memory.assessment_repo import (
    AssessmentRetrySchedule,
    DistressSnapshot,
    LastPHQ9Snapshot,
)


logging.basicConfig(level=logging.INFO)



@dataclass
class FakeRepoState:
    last: LastPHQ9Snapshot | None = None
    pending_retry: AssessmentRetrySchedule | None = None
    conversation_count: int = 5
    phq9_progress: dict[str, Any] | None = None
    distress: DistressSnapshot = DistressSnapshot(
        high_distress_session_count_7d=0,
        avg_emotion_valence_7d=None,
        recurring_trigger_active=False,
    )
    saved_results: list[Any] | None = None
    cleared_retries_for: list[str] | None = None
    scheduled_retries: list[tuple[str, int, str]] | None = None

    def __post_init__(self) -> None:
        self.saved_results = self.saved_results or []
        self.cleared_retries_for = self.cleared_retries_for or []
        self.scheduled_retries = self.scheduled_retries or []


class FakeAssessmentRepository:
    """stand-in"""

    def __init__(self, state: FakeRepoState | None = None) -> None:
        self.state = state or FakeRepoState()

    async def get_last_phq9(self, user_id: str) -> LastPHQ9Snapshot | None:
        return self.state.last

    async def get_conversation_count(self, user_id: str) -> int:
        return self.state.conversation_count

    async def get_pending_retry(
        self, user_id: str
    ) -> AssessmentRetrySchedule | None:
        return self.state.pending_retry

    async def get_distress_snapshot(self, user_id: str) -> DistressSnapshot:
        return self.state.distress

    async def save_phq9_result(self, result: Any) -> None:
        self.state.saved_results.append(result)

    async def schedule_retry(
        self, *, user_id: str, days: int, reason: str
    ) -> AssessmentRetrySchedule:
        sched = AssessmentRetrySchedule(
            user_id=user_id,
            next_attempt_at=datetime.now(timezone.utc),
            reason=reason,
        )
        self.state.scheduled_retries.append((user_id, days, reason))
        self.state.pending_retry = sched
        return sched

    async def clear_retry(self, user_id: str) -> None:
        self.state.cleared_retries_for.append(user_id)
        self.state.pending_retry = None

    async def load_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        return self.state.phq9_progress

    async def save_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        self.state.phq9_progress = dict(state)

    async def clear_phq9_progress(
        self,
        *,
        user_id: str,
        session_id: str,
    ) -> None:
        self.state.phq9_progress = None



class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeLLM:
    """respon"""

    def __init__(
        self,
        *,
        script: list[str] | None = None,
        responder: Any | None = None,
    ) -> None:
        self.script = list(script or [])
        self.responder = responder
        self.calls: list[list[Any]] = []

    async def ainvoke(self, messages: list[Any]) -> _FakeAIMessage:
        self.calls.append(messages)
        if self.responder is not None:
            user_text = ""
            for m in messages:
                cls_name = m.__class__.__name__
                msg_type = getattr(m, "type", "")
                # stand-in
                if "Human" in cls_name or msg_type == "human":
                    user_text = m.content
            return _FakeAIMessage(self.responder(user_text))
        if not self.script:
            return _FakeAIMessage('{"score": 0, "confidence": 1.0}')
        return _FakeAIMessage(self.script.pop(0))



@pytest.fixture
def fake_repo() -> FakeAssessmentRepository:
    return FakeAssessmentRepository()


@pytest.fixture
def scorer_llm_factory():
    """fake llm-json"""

    def builder() -> FakeLLM:
        import re as _re

        def respond(user_prompt: str) -> str:
            # match user
            m = _re.search(
                r'User answer:\s*"""\s*(.*?)\s*"""',
                user_prompt,
                _re.DOTALL,
            )
            answer = (m.group(1) if m else user_prompt).lower()

            if "ambig" in answer:
                return json.dumps({"score": 1, "confidence": 0.3})
            if "hampir setiap" in answer or "nearly every day" in answer:
                return json.dumps({"score": 3, "confidence": 0.95})
            if "lebih dari setengah" in answer or "more than half" in answer:
                return json.dumps({"score": 2, "confidence": 0.9})
            if "beberapa hari" in answer or "several days" in answer:
                return json.dumps({"score": 1, "confidence": 0.9})
            if "tidak sama sekali" in answer or "not at all" in answer:
                return json.dumps({"score": 0, "confidence": 0.95})
            stripped = answer.strip()
            if stripped in {"0", "1", "2", "3"}:
                return json.dumps({"score": int(stripped), "confidence": 0.99})
            return json.dumps({"score": 0, "confidence": 0.85})

        return FakeLLM(responder=respond)

    return builder


@pytest.fixture
def feedback_llm() -> FakeLLM:
    return FakeLLM(
        script=[
            "Skor PHQ-9 kamu menunjukkan gejala ringan. "
            "Terima kasih sudah meluangkan waktu menjawab. "
            "Kalau perlu, kita bisa lanjut ngobrol pelan-pelan."
        ]
    )

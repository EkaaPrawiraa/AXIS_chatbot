"""test-cli"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

# disable real import
os.environ.setdefault("AGENTIC_DISABLE_CONTEXT_BUILDER", "1")

from agentic.agent.audit.guardrail_events import (
    GuardrailEvent,
    NullGuardrailLogger,
)
from agentic.agent.cbt.techniques import CBTTechnique
from agentic.agent.nodes.crisis_guardrail import (
    crisis_escalation_node,
    crisis_guardrail_node,
)
from agentic.agent.nodes.dialogue_policy import dialogue_policy_node
from agentic.agent.nodes.input_guardrail import input_guardrail_node
from agentic.agent.nodes.memory_retrieval import memory_retrieval_node
from agentic.agent.nodes.output_guardrail import output_guardrail_node
from agentic.agent.nodes.phq9_check import phq9_check_node
from agentic.agent.nodes.phq9_delivery import phq9_delivery_node
from agentic.agent.nodes.response_generator import response_generator_node
from agentic.agent.nodes.session_end import session_end_node
from agentic.agent.nodes.speech_adapter import speech_adapter_node
from agentic.agent.nodes.speech_to_text import (
    TranscriptResult,
    speech_to_text_node,
)
from agentic.agent.nodes.text_to_speech import (
    TTSResult,
    text_to_speech_node,
)
from agentic.agent.session.activity_repo import (
    InMemorySessionActivityRepository,
)
from agentic.agent.session.finalizer import SessionFinalizer
from agentic.agent.session.sweeper import SessionSweeper, SweeperConfig
from agentic.agent.state import (
    ConversationState,
    empty_conversation_state,
)
from agentic.config.voices import load_voice_catalog
from agentic.memory.assessment_repo import (
    AssessmentRetrySchedule,
    DistressSnapshot,
    LastPHQ9Snapshot,
)


logging.basicConfig(level=logging.WARNING)



class _FakeAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


@dataclass
class FakeChatLLM:
    """chat gpt"""

    calls: list[Any] = field(default_factory=list)

    async def ainvoke(self, messages):
        self.calls.append(messages)
        user_text = ""
        for m in reversed(messages):
            cls = m.__class__.__name__
            if "Human" in cls or getattr(m, "type", "") == "human":
                user_text = m.content
                break
        lowered = user_text.lower()
        if "ujian" in lowered or "skripsi" in lowered:
            text = (
                "Kerasa berat ya kalau soal ujian. Apa bagian yang paling "
                "bikin pikiran berputar?"
            )
        elif "reframe" in lowered:
            text = (
                "Ayo kita lihat pikirannya pelan-pelan. Apa kata-kata "
                "tepat yang muncul di kepalamu tadi?"
            )
        else:
            text = "Aku denger. Cerita lebih ya, aku ada di sini."
        return _FakeAIMessage(text)


@dataclass
class FakeAdapterLLM:
    style: str = "v25"

    async def ainvoke(self, messages):
        text = ""
        for m in reversed(messages):
            cls = m.__class__.__name__
            if "Human" in cls or getattr(m, "type", "") == "human":
                text = m.content
                break
        if self.style == "v3":
            return _FakeAIMessage(
                "[softly] " + text + " [pause] [warmly] Kamu udah hebat."
            )
        return _FakeAIMessage(
            text.replace("Saya", "Aku").replace("saya", "aku")
        )


@dataclass
class FakeSTT:
    next_text: str = "halo, aku capek banget hari ini"

    async def transcribe(self, *, audio, mime, language_hint):
        return TranscriptResult(
            text=self.next_text, language="id", confidence=0.95,
        )


@dataclass
class FakeTTS:
    audio: bytes = b"\xff\xfb_audio"

    async def synthesize(self, *, text, voice, model, streaming):
        return TTSResult(
            provider="elevenlabs",
            model=model,
            audio_blob=self.audio,
            audio_format="mp3",
            streaming=streaming,
        )


@dataclass
class FakeOpenAITTSFallback:
    audio: bytes = b"\xff\xfb_openai_audio"

    async def synthesize(
        self, *, text, voice, model, instructions=None, response_format="mp3",
    ):
        return TTSResult(
            provider="openai_tts1",
            model=model,
            audio_blob=self.audio,
            audio_format=response_format,
        )


@dataclass
class FakeAssessmentRepo:
    last: LastPHQ9Snapshot | None = None
    pending: AssessmentRetrySchedule | None = None
    distress: DistressSnapshot = field(
        default_factory=lambda: DistressSnapshot(0, None, False)
    )

    async def get_last_phq9(self, _):
        return self.last

    async def get_pending_retry(self, _):
        return self.pending

    async def get_distress_snapshot(self, _):
        return self.distress

    async def save_phq9_result(self, r):
        pass

    async def schedule_retry(self, *, user_id, days, reason):
        self.pending = AssessmentRetrySchedule(
            user_id=user_id,
            next_attempt_at=datetime.now(timezone.utc),
            reason=reason,
        )
        return self.pending

    async def clear_retry(self, user_id):
        self.pending = None


# skip error


@dataclass
class Bot:
    audit: NullGuardrailLogger = field(default_factory=NullGuardrailLogger)
    chat_llm: FakeChatLLM = field(default_factory=FakeChatLLM)
    adapter_v25: FakeAdapterLLM = field(
        default_factory=lambda: FakeAdapterLLM("v25")
    )
    adapter_v3: FakeAdapterLLM = field(
        default_factory=lambda: FakeAdapterLLM("v3")
    )
    stt: FakeSTT = field(default_factory=FakeSTT)
    tts_primary: FakeTTS = field(default_factory=FakeTTS)
    tts_fallback: FakeOpenAITTSFallback = field(
        default_factory=FakeOpenAITTSFallback
    )
    catalog: Any = field(
        default_factory=lambda: load_voice_catalog(force_reload=True)
    )
    assessment: FakeAssessmentRepo = field(default_factory=FakeAssessmentRepo)
    activity: InMemorySessionActivityRepository = field(
        default_factory=InMemorySessionActivityRepository
    )

    async def turn(self, state: ConversationState) -> ConversationState:
        # stt audio_input
        if (state.get("voice_state") or {}).get("audio_input") is not None:
            state = await speech_to_text_node(
                state, provider=self.stt, audit=self.audit,
            )

        state = await input_guardrail_node(state, audit=self.audit)
        if (state.get("input_guardrail") or {}).get("decision") == "escalate_crisis":
            state = await crisis_escalation_node(state, audit=self.audit)
            return await self._finish(state)

        state = await phq9_check_node(state, repo=self.assessment)
        state = await crisis_guardrail_node(state, audit=self.audit)
        if state.get("safety_flag") == "crisis":
            state = await crisis_escalation_node(state, audit=self.audit)
            return await self._finish(state)

        state = await memory_retrieval_node(state, audit=self.audit)
        state = await dialogue_policy_node(state, audit=self.audit)

        phq_phase = (state.get("phq9_state") or {}).get("phase", "idle")
        ran_phq = False
        if phq_phase in ("offer_pending", "offered", "in_progress", "awaiting_clar"):
            state = await phq9_delivery_node(
                state,
                repo=self.assessment,
                scorer_llm=None,
                feedback_llm=self.chat_llm,
            )
            ran_phq = True

        # sikap diam
        if not (state.get("response_draft") or "").strip() and not state.get("final_response"):
            state = await response_generator_node(
                state, llm=self.chat_llm, audit=self.audit,
            )

        state = await output_guardrail_node(
            state, audit=self.audit, rewrite_llm=self.chat_llm,
        )

        if (state.get("phq9_state") or {}).get("route_to_crisis_after"):
            state = await crisis_escalation_node(state, audit=self.audit)

        return await self._finish(state)

    async def _finish(self, state: ConversationState) -> ConversationState:
        if (state.get("voice_state") or {}).get("output_modality") in ("voice", "both"):
            state = await speech_adapter_node(
                state,
                audit=self.audit,
                llm_v25=self.adapter_v25,
                llm_v3=self.adapter_v3,
            )
            state = await text_to_speech_node(
                state,
                elevenlabs=self.tts_primary,
                openai_tts=self.tts_fallback,
                catalog=self.catalog,
                audit=self.audit,
            )
        state = await session_end_node(
            state, activity_repo=self.activity, audit=self.audit,
        )
        return state



def _build_inert_finalizer() -> SessionFinalizer:
    async def _loader(*, session_id, user_id):
        return []

    async def _summarize(*, transcript, language):
        return "(no summary in test bot)"

    async def _extract(*, message, user_id, session_id, language):
        return {"experience": {"description": message}}

    async def _writer(*, user_id, session_id, summary, extracted, language):
        print(
            f"     [finalize] session={session_id} extracted={len(extracted)}"
        )

    return SessionFinalizer(
        history_loader=_loader,
        summarizer=_summarize,
        extractor=_extract,
        kg_writer=_writer,
    )



HELP_TEXT = """\
Commands:
  /help                       this help
  /quit | /exit               exit
  /voice on | off             toggle voice modality
  /lang id | en               set resolved_language
  /reset                      new session
  /state                      print abbreviated state
  /audit [N]                  last N audit events (default 10)
  /sweeper run                trigger one sweeper iteration
  /sweeper aged N             age current session by N minutes
  /force phq9 offer           force PHQ-9 offer phase
  /force crisis-input         next turn injects a crisis keyword
"""


def _short_state(state: ConversationState) -> str:
    voice = state.get("voice_state") or {}
    phq9 = state.get("phq9_state") or {}
    cbt = state.get("cbt_state") or {}
    summary = {
        "session_turn": state.get("session_turn"),
        "resolved_language": state.get("resolved_language"),
        "safety_flag": state.get("safety_flag"),
        "input_guardrail": (state.get("input_guardrail") or {}).get("decision"),
        "phq9.phase": phq9.get("phase"),
        "phq9.active_item": phq9.get("active_item"),
        "phq9.route_to_crisis_after": phq9.get("route_to_crisis_after"),
        "cbt.last_offered": cbt.get("last_offered"),
        "cbt_node_active": state.get("cbt_node_active"),
        "voice.output_modality": voice.get("output_modality"),
        "voice.tts_provider": voice.get("tts_provider"),
        "voice.tts_streaming": voice.get("tts_streaming"),
        "audio_blob_bytes": (
            len(voice.get("audio_output_blob") or b"")
            if isinstance(voice.get("audio_output_blob"), (bytes, bytearray))
            else 0
        ),
        "messages": len(state.get("messages") or []),
    }
    return json.dumps(summary, indent=2, default=str, ensure_ascii=False)


@dataclass
class _Flags:
    use_voice: bool = False
    inject_crisis_next: bool = False


async def _handle_command(
    cmd: str,
    *,
    bot: Bot,
    state: ConversationState,
    sweeper: SessionSweeper,
    flags: _Flags,
) -> str | None:
    parts = cmd.split()
    head = parts[0]
    rest = parts[1:]

    if head in ("/quit", "/exit"):
        return "quit"
    if head == "/help":
        print(HELP_TEXT)
        return None
    if head == "/state":
        print(_short_state(state))
        return None
    if head == "/audit":
        n = int(rest[0]) if rest else 10
        for e in bot.audit.events[-n:]:
            print(" ", e.to_log_line())
        return None
    if head == "/voice" and rest:
        flags.use_voice = rest[0].lower() == "on"
        voice = dict(state.get("voice_state") or {})
        voice["output_modality"] = "voice" if flags.use_voice else "text"
        state["voice_state"] = voice
        print(f"     voice mode: {'on' if flags.use_voice else 'off'}")
        return None
    if head == "/lang" and rest:
        state["resolved_language"] = rest[0]
        print(f"     resolved_language = {rest[0]}")
        return None
    if head == "/reset":
        new_uid = state.get("user_id") or "u"
        new_sid = "s" + str(int(datetime.now().timestamp()) % 100000)
        fresh = empty_conversation_state(
            user_id=new_uid, session_id=new_sid, language_pref="id",
        )
        for k in list(state.keys()):
            state.pop(k, None)
        for k, v in fresh.items():
            state[k] = v
        state["resolved_language"] = "id"
        flags.use_voice = False
        flags.inject_crisis_next = False
        print(f"     reset to session {new_sid}")
        return None
    if head == "/sweeper" and rest:
        sub = rest[0]
        if sub == "run":
            handled = await sweeper.run_once()
            print(f"     sweeper handled {len(handled)} session(s)")
            return None
        if sub == "aged" and len(rest) > 1:
            mins = int(rest[1])
            sid = state.get("session_id") or ""
            row = bot.activity._rows.get(sid)
            if row:
                row.last_activity_at = (
                    datetime.now(timezone.utc) - timedelta(minutes=mins)
                )
                row.ai_was_last_speaker = True
                print(f"     aged session {sid} by {mins} minutes")
            else:
                print(
                    f"     session {sid} not in activity repo yet; "
                    "send a message first"
                )
            return None
    if head == "/force" and rest:
        what = rest[0]
        if what == "phq9" and len(rest) > 1 and rest[1] == "offer":
            phq = dict(state.get("phq9_state") or {})
            phq["phase"] = "offer_pending"
            phq["tier"] = "scheduled"
            phq["language"] = state.get("resolved_language") or "id"
            state["phq9_state"] = phq
            print("     phq9 forced to offer_pending")
            return None
        if what == "crisis-input":
            flags.inject_crisis_next = True
            print("     next turn will inject crisis keyword")
            return None

    print("     unknown command. /help for list")
    return None


async def _repl() -> None:
    bot = Bot()
    user_id = str(uuid.uuid4())[:8]
    session_id = str(uuid.uuid4())[:8]
    state = empty_conversation_state(
        user_id=user_id, session_id=session_id, language_pref="id",
    )
    state["resolved_language"] = "id"
    flags = _Flags()

    print("=" * 60)
    print(" Companionship Chatbot - full-flow test bot")
    print(f" user_id    = {user_id}")
    print(f" session_id = {session_id}")
    print(" Type /help for commands, /quit to exit")
    print("=" * 60)

    sweeper = SessionSweeper(
        repo=bot.activity,
        finalizer=_build_inert_finalizer(),
        config=SweeperConfig(idle_minutes=30, batch_limit=10, max_attempts=2),
    )

    while True:
        try:
            user_text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue

        if user_text.startswith("/"):
            done = await _handle_command(
                user_text,
                bot=bot, state=state, sweeper=sweeper, flags=flags,
            )
            if done == "quit":
                break
            continue

        # init state
        turn_state = dict(state)
        if flags.inject_crisis_next:
            turn_state["current_message"] = "ingin mati aja rasanya"
            flags.inject_crisis_next = False
        elif flags.use_voice:
            voice = dict(turn_state.get("voice_state") or {})
            voice["audio_input"] = b"<fake-audio>"
            voice["audio_input_mime"] = "audio/wav"
            voice["output_modality"] = "voice"
            bot.stt.next_text = user_text
            turn_state["voice_state"] = voice
        else:
            voice = dict(turn_state.get("voice_state") or {})
            voice["output_modality"] = "text"
            voice["audio_input"] = None
            turn_state["voice_state"] = voice
            turn_state["current_message"] = user_text

        new_state = await bot.turn(turn_state)
        for k, v in new_state.items():
            state[k] = v

        reply = state.get("final_response") or state.get("response_draft") or ""
        print(f"\nbot> {reply}")
        voice = state.get("voice_state") or {}
        if voice.get("audio_output_blob"):
            blob = voice["audio_output_blob"]
            blen = len(blob) if isinstance(blob, (bytes, bytearray)) else 0
            print(
                f"     [audio synthesized via {voice.get('tts_provider')}, "
                f"{blen} bytes]"
            )


def main() -> int:
    try:
        asyncio.run(_repl())
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

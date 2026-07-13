"""exec"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Mapping
from typing import Any

from agentic.agent.audit.guardrail_events import PostgresGuardrailLogger
from agentic.agent.graph import build_graph
from agentic.agent.audit.graph_trace import persist_graph_audit
from agentic.agent.session.activity_repo import (
    PostgresSessionActivityRepository,
)
from agentic.agent.state import ConversationState, empty_conversation_state
from agentic.agent.tools import get_default_toolset
from agentic.config.llm_models import (
    CBT_JUDGE,
    CRISIS_EMPATHY,
    GUARDRAIL_REWRITE,
    PHQ9_CLARIFICATION_EXPLAINER,
    PHQ9_FEEDBACK,
    PHQ9_JUDGE,
    PHQ9_SCORER,
    RESPONSE_GENERATOR,
    SPEECH_ADAPTER,
    SPEECH_ADAPTER_V3,
    build_llm,
    llm_provider,
)
from agentic.config.voices import load_voice_catalog
from agentic.gateway.model import (
    ChatTurnRequest,
    ChatTurnResponse,
    SynthesizeSpeechRequest,
    SynthesizeSpeechResponse,
    TranscribeSpeechRequest,
    TranscribeSpeechResponse,
    VoiceTurnResponse,
)
from agentic.memory.assessment_repo import AssessmentRepository
from agentic.memory.pg_vector.client import get_neo4j, get_pool


logger = logging.getLogger(__name__)
state_logger = logging.getLogger("uvicorn.error")


# `whitelist`, `sse`, `else`, `suppress`.
_STREAM_TOKEN_NODES = frozenset({
    "response_generator",
    "crisis_empathy",
})


def _state_logging_enabled() -> bool:
    return os.getenv("AXIS_GRAPH_STATE_LOG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "debug",
    }


def _timing_logging_enabled() -> bool:
    return os.getenv("AXIS_GRAPH_TIMING_LOG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "debug",
    }


class _GraphTimingTracker:
    """ekstrak durasi, emit."""

    _START_EVENTS = {
        "on_chain_start",
        "on_tool_start",
        "on_chat_model_start",
        "on_llm_start",
    }
    _END_EVENTS = {
        "on_chain_end",
        "on_tool_end",
        "on_chat_model_end",
        "on_llm_end",
    }

    def __init__(
        self,
        *,
        user_id: str,
        session_id: str,
        request_kind: str,
    ) -> None:
        self._user_id = user_id
        self._session_id = session_id
        self._request_kind = request_kind
        self._starts: dict[str, float] = {}
        self._totals_ms: dict[str, float] = defaultdict(float)
        self._counts: dict[str, int] = defaultdict(int)

    @staticmethod
    def _coerce_run_id(value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _event_label(event: Mapping[str, Any]) -> str:
        name = str(event.get("name") or "")
        metadata = event.get("metadata") or {}
        node = metadata.get("langgraph_node") or ""
        if node:
            return f"{name}::{node}" if name else str(node)
        return name or "(unknown)"

    def observe(self, event: Mapping[str, Any]) -> None:
        kind = str(event.get("event") or "")
        if kind not in self._START_EVENTS and kind not in self._END_EVENTS:
            return

        run_id = self._coerce_run_id(event.get("run_id"))
        if not run_id:
            return

        if kind in self._START_EVENTS:
            self._starts[run_id] = time.perf_counter()
            return

        start = self._starts.pop(run_id, None)
        if start is None:
            return

        duration_ms = (time.perf_counter() - start) * 1000.0
        label = self._event_label(event)
        self._totals_ms[label] += duration_ms
        self._counts[label] += 1

        state_logger.info(
            "GraphTiming %s",
            {
                "user_id": self._user_id,
                "session_id": self._session_id,
                "request_kind": self._request_kind,
                "event": kind,
                "name": str(event.get("name") or ""),
                "label": label,
                "duration_ms": round(duration_ms, 3),
            },
        )

    def log_summary(self, *, top_n: int = 12) -> None:
        if not self._totals_ms:
            return
        ranked = sorted(self._totals_ms.items(), key=lambda x: x[1], reverse=True)
        summary = [
            {
                "label": label,
                "total_ms": round(total_ms, 3),
                "count": self._counts.get(label, 0),
                "avg_ms": round(total_ms / max(self._counts.get(label, 1), 1), 3),
            }
            for label, total_ms in ranked[: max(top_n, 1)]
        ]
        state_logger.info(
            "GraphTimingSummary %s",
            {
                "user_id": self._user_id,
                "session_id": self._session_id,
                "request_kind": self._request_kind,
                "top": summary,
            },
        )


class ChatGraphService:
    """build prod langgraph invoke"""

    def __init__(self) -> None:
        self._graph: Any | None = None
        self._lock = asyncio.Lock()

    async def invoke(
        self, request: ChatTurnRequest | Mapping[str, Any]
    ) -> ChatTurnResponse:
        """run chat, return full resp"""
        normalized = self._coerce_request(request)
        graph = await self._get_graph()
        state = self._request_to_state(normalized)

        timing_enabled = _timing_logging_enabled()
        tracker = (
            _GraphTimingTracker(
                user_id=normalized.user_id,
                session_id=normalized.session_id,
                request_kind="invoke",
            )
            if timing_enabled
            else None
        )

        if not timing_enabled:
            result = await graph.ainvoke(state)
        else:
            final_output: dict[str, Any] | None = None
            async for event in graph.astream_events(state, version="v2"):
                if tracker is not None:
                    tracker.observe(event)
                if (
                    event.get("event") == "on_chain_end"
                    and event.get("name") == "LangGraph"
                ):
                    final_output = event.get("data", {}).get("output") or {}
            if tracker is not None:
                tracker.log_summary()
            if final_output is None:
                raise RuntimeError("LangGraph event stream ended without output")
            result = final_output

        self._log_conversation_state(result)
        await persist_graph_audit(result)
        return self._state_to_response(
            result, include_state=normalized.include_state
        )

    async def synthesize_speech(
        self, request: SynthesizeSpeechRequest | Mapping[str, Any]
    ) -> SynthesizeSpeechResponse:
        """synthetize text"""
        normalized = self._coerce_synthesize_request(request)
        text = normalized.text.strip()
        if not text:
            raise ValueError("text is required")

        from agentic.agent.nodes.speech_adapter import speech_adapter_node
        from agentic.agent.nodes.text_to_speech import (
            OpenAITTSClient,
            run_tts_fallback_chain,
        )
        from agentic.agent.state import (
            empty_conversation_state,
            empty_voice_state,
        )

        catalog = load_voice_catalog()
        voice_entry = catalog.get(
            normalized.voice_id,
            language=normalized.language_pref,
        )

        # build, run, take.
        adapter_state: ConversationState = empty_conversation_state(
            user_id="00000000-0000-0000-0000-000000000000",
            session_id="00000000-0000-0000-0000-000000000000",
        )
        adapter_state["final_response"] = text
        # mode carries tts_model_choice.
        mode = normalized.tts_model or "v2_5_turbo"
        adapter_voice = dict(empty_voice_state())
        adapter_voice["output_modality"] = "voice"
        adapter_voice["voice_id"] = voice_entry.id
        adapter_voice["tts_model"] = "v3" if mode == "v3" else "v2_5_turbo"
        adapter_state["voice_state"] = adapter_voice  # type: ignore[typeddict-item]

        try:
            adapter_state = await speech_adapter_node(adapter_state)
        except Exception as exc:
            logger.warning(
                "synthesize_speech: speech_adapter failed (%s); "
                "falling back to raw input text",
                exc,
            )

        adapted_voice = adapter_state.get("voice_state") or {}
        plain_text = (
            str(adapted_voice.get("speech_response") or "").strip() or text
        )
        # buat ngisap tag.
        spoken_text = plain_text
        if adapted_voice.get("tts_model") == "v3":
            tagged = str(adapted_voice.get("speech_response_tags") or "").strip()
            if tagged:
                spoken_text = tagged

        if mode == "openai_tts1":
            # skip Gemini entirely
            openai_model = os.getenv("OPENAI_TTS_MODEL") or catalog.openai_tts_model
            result = await OpenAITTSClient().synthesize(
                text=plain_text,
                voice=voice_entry,
                model=openai_model,
                instructions=catalog.openai_tts_instructions,
                response_format=(
                    os.getenv("OPENAI_TTS_FORMAT") or catalog.openai_tts_format
                ),
            )
        else:
            # skip hardcode
            outcome = await run_tts_fallback_chain(
                text=spoken_text,
                voice_entry=voice_entry,
                mode=mode,
                empathetic=False,
                catalog=catalog,
                streaming=False,
            )
            result = outcome.result
        audio_output_base64 = None
        if isinstance(result.audio_blob, (bytes, bytearray)):
            audio_output_base64 = base64.b64encode(result.audio_blob).decode("ascii")

        return SynthesizeSpeechResponse(
            audio_output_base64=audio_output_base64,
            audio_output_format=result.audio_format,
            tts_provider=result.provider,
            voice_id=voice_entry.id,
            voice_provider_id=voice_entry.elevenlabs_voice_id,
            tts_model=result.model,
            voice_error=result.error,
        )

    async def transcribe_speech(
        self, request: TranscribeSpeechRequest | Mapping[str, Any]
    ) -> TranscribeSpeechResponse:
        """stt"""
        if not isinstance(request, TranscribeSpeechRequest):
            request = TranscribeSpeechRequest.model_validate(dict(request))

        from agentic.agent.nodes.speech_to_text import speech_to_text_node
        from agentic.agent.state import empty_conversation_state, empty_voice_state

        audio_bytes = base64.b64decode(request.audio_base64)

        state: ConversationState = empty_conversation_state(
            user_id="00000000-0000-0000-0000-000000000000",
            session_id="00000000-0000-0000-0000-000000000000",
        )
        state["language_pref"] = request.language_pref
        voice_state = dict(empty_voice_state())
        voice_state["audio_input"] = audio_bytes
        voice_state["audio_input_mime"] = request.audio_mime
        state["voice_state"] = voice_state  # type: ignore[typeddict-item]

        state = await speech_to_text_node(state)
        result_voice = state.get("voice_state") or {}

        return TranscribeSpeechResponse(
            text=str(result_voice.get("transcript") or ""),
            language=result_voice.get("transcript_language"),
            confidence=result_voice.get("transcript_confidence"),
            voice_error=result_voice.get("voice_error"),
        )

    async def stream(
        self, request: ChatTurnRequest | Mapping[str, Any]
    ) -> AsyncIterator[dict[str, str]]:
        """ntokens', 'res', 'prod"""
        normalized = self._coerce_request(request)
        graph = await self._get_graph()
        state = self._request_to_state(normalized)

        tracker = (
            _GraphTimingTracker(
                user_id=normalized.user_id,
                session_id=normalized.session_id,
                request_kind="stream",
            )
            if _timing_logging_enabled()
            else None
        )
        summary_logged = False

        try:
            async for event in graph.astream_events(state, version="v2"):
                if tracker is not None:
                    tracker.observe(event)

                kind: str = event.get("event", "")

                if kind == "on_chat_model_stream":
                    # limit to user nodes
                    metadata = event.get("metadata") or {}
                    node = metadata.get("langgraph_node") or ""
                    if node not in _STREAM_TOKEN_NODES:
                        continue
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is None:
                        continue
                    content = (
                        chunk.content
                        if hasattr(chunk, "content")
                        else str(chunk)
                    )
                    if content:
                        yield {"event": "token", "data": content}

                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event.get("data", {}).get("output") or {}
                    self._log_conversation_state(output)
                    await persist_graph_audit(output)
                    response = self._state_to_response(
                        output, include_state=normalized.include_state
                    )
                    if tracker is not None and not summary_logged:
                        tracker.log_summary()
                        summary_logged = True
                    yield {"event": "done", "data": response.model_dump_json()}

        except Exception as exc:
            if tracker is not None and not summary_logged:
                tracker.log_summary()
            logger.error("stream error for session=%s: %s", normalized.session_id, exc)
            yield {"event": "error", "data": "An error occurred during streaming."}

    async def _get_graph(self) -> Any:
        if self._graph is not None:
            return self._graph

        async with self._lock:
            if self._graph is not None:
                return self._graph

            self._graph = await self._build_graph_once()
            self.draw_graph_image()
            return self._graph

    def draw_graph_image(self) -> None:
        """buat nyimpen langgraph"""
        if self._graph is None:
            return

        output_path = os.getenv("AXIS_GRAPH_IMAGE_PATH", "graph.png").strip() or "graph.png"
        background = os.getenv("AXIS_GRAPH_IMAGE_BG", "white").strip() or "white"

        try:
            padding = int(os.getenv("AXIS_GRAPH_IMAGE_PADDING", "24"))
        except ValueError:
            padding = 24

        try:
            wrap_words = int(os.getenv("AXIS_GRAPH_IMAGE_WRAP_WORDS", "6"))
        except ValueError:
            wrap_words = 6

        theme = os.getenv("AXIS_GRAPH_IMAGE_THEME", "neutral").strip() or "neutral"
        font_family = os.getenv(
            "AXIS_GRAPH_IMAGE_FONT_FAMILY",
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto",
        ).strip()

        # ignoring unk keys
        frontmatter_config: dict[str, Any] = {
            "config": {
                "theme": theme,
                "themeVariables": {
                    "fontFamily": font_family,
                    "fontSize": "16px",
                },
            }
        }

        try:
            self._graph.get_graph().draw_mermaid_png(
                output_file_path=output_path,
                background_color=background,
                padding=padding,
                wrap_label_n_words=wrap_words,
                frontmatter_config=frontmatter_config,
            )
            logger.info("Graph visualization saved: %s", output_path)
        except Exception as exc:
            logger.warning("Could not generate graph visualization: %s", exc)

    async def _build_graph_once(self) -> Any:
        """resolve deps & compile."""
        pool = await get_pool()
        if pool is None:
            raise RuntimeError(
                "Postgres unavailable. Start DB and check PG_* env."
            )

        neo4j = await get_neo4j()
        if neo4j is None:
            raise RuntimeError(
                "Neo4j unavailable. Start KG and check NEO4J_* env."
            )

        try:
            from agentic.memory.neo4j_client import init_client as _init_neo4j

            await _init_neo4j()
        except Exception as exc:
            raise RuntimeError(
                f"neo4j_client init failed: {exc}"
            ) from exc

        stt_provider = self._build_stt()
        elevenlabs, openai_tts = self._build_tts_providers()
        context_builder = self._wrap_context_builder()

        assessment_repo = AssessmentRepository(
            pg_pool=pool, neo4j_driver=neo4j,
        )

        graph = build_graph(
            assessment_repo=assessment_repo,
            audit_logger=PostgresGuardrailLogger(pool),
            activity_repo=PostgresSessionActivityRepository(pg_pool=pool),
            voice_catalog=load_voice_catalog(force_reload=True),
            stt_provider=stt_provider,
            elevenlabs_tts=elevenlabs,
            openai_tts=openai_tts,
            context_builder=context_builder,
            response_llm=build_llm(RESPONSE_GENERATOR),
            response_tools=get_default_toolset(),
            scorer_llm=build_llm(PHQ9_SCORER),
            phq9_judge_llm=build_llm(PHQ9_JUDGE),
            phq9_clarification_llm=build_llm(PHQ9_CLARIFICATION_EXPLAINER),
            cbt_judge_llm=build_llm(CBT_JUDGE),
            feedback_llm=build_llm(PHQ9_FEEDBACK),
            rewrite_llm=build_llm(GUARDRAIL_REWRITE),
            speech_adapter_llm_v25=build_llm(SPEECH_ADAPTER),
            speech_adapter_llm_v3=build_llm(SPEECH_ADAPTER_V3),
            crisis_empathy_llm=build_llm(CRISIS_EMPATHY),
        )
        logger.info(
            "ChatGraphService graph compiled; "
            "tools=%d, postgres=ok, neo4j=ok, stt=%s, elevenlabs=%s, openai_tts=%s, "
            "crisis_tier1=deterministic, crisis_tier2=llm(%s)",
            len(get_default_toolset()),
            "ok" if stt_provider else "off",
            "ok" if elevenlabs else "off",
            "ok" if openai_tts else "off",
            CRISIS_EMPATHY.model,
        )
        return graph

    @staticmethod
    def _log_conversation_state(state: ConversationState) -> None:
        if not _state_logging_enabled():
            return
        voice = state.get("voice_state") or {}
        state_logger.info(
            "ConversationState %s",
            {
                "user_id": state.get("user_id"),
                "session_id": state.get("session_id"),
                "messages": len(state.get("messages") or []),
                "current_message_chars": len(
                    (state.get("current_message") or "").strip()
                ),
                "session_turn": state.get("session_turn"),
                "language_pref": state.get("language_pref"),
                "profile_context_loaded": bool(state.get("profile_context")),
                "resolved_language": state.get("resolved_language"),
                "linguistic_signals": state.get("linguistic_signals"),
                "safety_flag": state.get("safety_flag"),
                "crisis_tier": state.get("crisis_tier"),
                "deferred_crisis_signal": state.get("deferred_crisis_signal"),
                "input_guardrail": state.get("input_guardrail"),
                "kg_context": bool(state.get("kg_context")),
                "response_draft_chars": len(state.get("response_draft") or ""),
                "final_response_chars": len(state.get("final_response") or ""),
                "cbt_node_active": state.get("cbt_node_active"),
                "cbt_directive": state.get("cbt_directive"),
                "cbt_state": state.get("cbt_state"),
                "voice_state": {
                    "audio_input": voice.get("audio_input") is not None,
                    "audio_input_mime": voice.get("audio_input_mime"),
                    "output_modality": voice.get("output_modality"),
                    "voice_id": voice.get("voice_id"),
                    "tts_model": voice.get("tts_model"),
                    "transcript": bool(voice.get("transcript")),
                    "speech_response_chars": len(voice.get("speech_response") or ""),
                    "voice_error": voice.get("voice_error"),
                },
                "phq9_state": state.get("phq9_state"),
            },
        )

    @staticmethod
    def _build_stt() -> Any | None:
        """skip klo error"""
        from agentic.agent.nodes.speech_to_text import (
            GeminiTranscriptionProvider,
            OpenAITranscriptionProvider,
        )

        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_gemini = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        if not has_openai and not has_gemini:
            logger.warning(
                "Neither OPENAI_API_KEY nor GOOGLE_API_KEY/GEMINI_API_KEY set; "
                "STT (voice transcription) unavailable, text chat is unaffected",
            )
            return None

        prefer_gemini = llm_provider() != "openai"
        if prefer_gemini and has_gemini:
            return GeminiTranscriptionProvider()
        if not prefer_gemini and has_openai:
            return OpenAITranscriptionProvider()
        # buat nyimpen config
        return GeminiTranscriptionProvider() if has_gemini else OpenAITranscriptionProvider()

    @staticmethod
    def _build_tts_providers() -> tuple[Any | None, Any | None]:
        """build providers lazy"""
        from agentic.agent.nodes.text_to_speech import (
            ElevenLabsClient,
            OpenAITTSClient,
        )

        elevenlabs = (
            ElevenLabsClient() if os.getenv("ELEVENLABS_API_KEY") else None
        )
        openai_tts = (
            OpenAITTSClient() if os.getenv("OPENAI_API_KEY") else None
        )
        has_gemini = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
        if elevenlabs is None and openai_tts is None and not has_gemini:
            logger.warning(
                "No TTS providers configured; voice output will fail",
            )
        return elevenlabs, openai_tts

    @staticmethod
    def _wrap_context_builder():
        """bridge node"""
        async def _bridge(*, user_id, session_id, query, language):
            try:
                from agentic.memory.context_builder import build_context
                from agentic.memory.pg_vector import embed_text

                del session_id, language

                query_embedding = None
                if query and query.strip():
                    try:
                        query_embedding = await embed_text(query)
                    except Exception as exc:
                        logger.warning(
                            "context_builder embed_text failed: %s", exc,
                        )
                        query_embedding = None

                ctx = await build_context(
                    user_id=user_id,
                    query_embedding=query_embedding,
                    query_text=query,
                )
                if hasattr(ctx, "as_prompt_block"):
                    return ctx.as_prompt_block()
                return str(ctx) if ctx else ""
            except Exception as exc:
                logger.warning(
                    "context_builder bridge raised, returning empty: %s",
                    exc,
                )
                return ""

        return _bridge

    @staticmethod
    def _coerce_request(
        request: ChatTurnRequest | Mapping[str, Any]
    ) -> ChatTurnRequest:
        """`ng-normalize`"""
        if isinstance(request, ChatTurnRequest):
            return request
        return ChatTurnRequest.model_validate(request)

    @staticmethod
    def _coerce_synthesize_request(
        request: SynthesizeSpeechRequest | Mapping[str, Any]
    ) -> SynthesizeSpeechRequest:
        if isinstance(request, SynthesizeSpeechRequest):
            return request
        return SynthesizeSpeechRequest.model_validate(request)

    @classmethod
    def _request_to_state(
        cls, request: ChatTurnRequest | Mapping[str, Any]
    ) -> ConversationState:
        """ngambil data"""
        request = cls._coerce_request(request)
        state = empty_conversation_state(
            user_id=request.user_id,
            session_id=request.session_id,
            language_pref=request.language_pref,
        )
        state["messages"] = [m.model_dump() for m in request.messages]
        state["current_message_id"] = request.current_message_id
        state["current_message"] = request.current_message or ""
        state["session_turn"] = request.session_turn
        state["preferred_response_model"] = request.preferred_response_model
        state["resolved_language"] = request.resolved_language
        state["confession_mode"] = request.confession_mode
        state["single_pass_voice"] = request.single_pass_voice
        if request.linguistic_signals is not None:
            state["linguistic_signals"] = request.linguistic_signals  # type: ignore[typeddict-item]
        state["safety_flag"] = request.safety_flag
        state["kg_context"] = request.kg_context
        state["cbt_node_active"] = request.cbt_node_active
        state["cbt_directive"] = request.cbt_directive
        if request.cbt_state is not None:
            state["cbt_state"] = request.cbt_state  # type: ignore[typeddict-item]
        # init state
        if request.phq9_state is not None and request.session_turn > 1:
            state["phq9_state"] = request.phq9_state  # type: ignore[typeddict-item]

        voice = dict(state.get("voice_state") or {})
        voice["audio_input"] = request.voice.decoded_audio_input()
        voice["audio_input_mime"] = request.voice.audio_input_mime
        voice["output_modality"] = request.voice.output_modality
        voice["voice_id"] = request.voice.voice_id
        voice["tts_model"] = request.voice.tts_model
        if request.voice.tts_streaming is not None:
            voice["tts_streaming"] = request.voice.tts_streaming
        state["voice_state"] = voice  # type: ignore[typeddict-item]
        return state

    @staticmethod
    def _state_to_response(
        state: ConversationState, *, include_state: bool,
    ) -> ChatTurnResponse:
        """serialize into resp"""
        voice = dict(state.get("voice_state") or {})
        audio_blob = voice.get("audio_output_blob")
        audio_output_base64 = None
        if isinstance(audio_blob, (bytes, bytearray)):
            audio_output_base64 = base64.b64encode(audio_blob).decode("ascii")

        response_state: dict[str, Any] | None = None
        if include_state:
            response_state = dict(state)
            if response_state.get("voice_state"):
                response_voice = dict(response_state["voice_state"])
                response_voice.pop("audio_input", None)
                response_voice.pop("audio_output_blob", None)
                response_state["voice_state"] = response_voice

        return ChatTurnResponse(
            user_id=state.get("user_id", ""),
            session_id=state.get("session_id", ""),
            reply=state.get("final_response") or state.get("response_draft") or "",
            messages=list(state.get("messages") or []),
            session_turn=state.get("session_turn"),
            resolved_language=state.get("resolved_language"),
            linguistic_signals=state.get("linguistic_signals"),
            safety_flag=state.get("safety_flag"),
            crisis_tier=state.get("crisis_tier"),
            kg_context=state.get("kg_context"),
            cbt_node_active=state.get("cbt_node_active"),
            cbt_directive=state.get("cbt_directive"),
            cbt_state=state.get("cbt_state"),
            phq9_state=state.get("phq9_state"),
            voice=VoiceTurnResponse(
                transcript=voice.get("transcript"),
                transcript_confidence=voice.get("transcript_confidence"),
                transcript_language=voice.get("transcript_language"),
                output_modality=voice.get("output_modality"),
                voice_id=voice.get("voice_id"),
                voice_provider_id=voice.get("voice_provider_id"),
                speech_response=voice.get("speech_response"),
                speech_response_tags=voice.get("speech_response_tags"),
                tts_model=voice.get("tts_model"),
                tts_provider=voice.get("tts_provider"),
                tts_streaming=voice.get("tts_streaming"),
                audio_output_base64=audio_output_base64,
                audio_output_url=voice.get("audio_output_url"),
                audio_output_format=voice.get("audio_output_format"),
                voice_error=voice.get("voice_error"),
            ),
            state=response_state,
        )

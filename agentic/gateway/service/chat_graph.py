"""Runtime service for chat graph execution."""

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


# Whitelist of LangGraph nodes whose LLM token stream is forwarded to the
# client as SSE `token` events. Anything else — PHQ-9 / CBT judges that
# emit JSON action payloads, KG extractor, session summariser, speech
# adapter (TTS prep), output guardrail rewriter — is suppressed so its
# internal text does not bleed into the user-facing subtitle.
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
    """Collect and emit per-run wall-time timings from LangChain/LangGraph events."""

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
    """Build once and invoke the production LangGraph for chat turns."""

    def __init__(self) -> None:
        self._graph: Any | None = None
        self._lock = asyncio.Lock()

    async def invoke(
        self, request: ChatTurnRequest | Mapping[str, Any]
    ) -> ChatTurnResponse:
        """Run one chat turn through the LangGraph DAG, returning the full response."""
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
        return self._state_to_response(
            result, include_state=normalized.include_state
        )

    async def synthesize_speech(
        self, request: SynthesizeSpeechRequest | Mapping[str, Any]
    ) -> SynthesizeSpeechResponse:
        """Synthesize one text snippet without running a full chat turn.

        Pipeline mirrors the chat-turn voice flow:
            raw text → speech_adapter_node → TTS
        The adapter rewrites the snippet for natural spoken delivery
        (strips markdown, expands punctuation into pauses, injects v3
        prosody tags when applicable) so the standalone synthesize
        endpoint produces audio that sounds the same as the in-turn
        voice output. The endpoint stays stateless — we build a
        throwaway ConversationState only to drive the adapter.
        """
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

        # Build a one-shot state, run the adapter, take the rewritten text.
        # The standalone synthesize endpoint has no real user/session
        # context — supply zero-UUIDs so the TypedDict shape is satisfied.
        adapter_state: ConversationState = empty_conversation_state(
            user_id="00000000-0000-0000-0000-000000000000",
            session_id="00000000-0000-0000-0000-000000000000",
        )
        adapter_state["final_response"] = text
        # mode carries the caller's real tts_model choice (ElevenLabs
        # v2_5_turbo/v3, the "openai_tts1" force-OpenAI sentinel, or a
        # Gemini tier alias like "gemini-2.5-pro-tts") straight through --
        # collapsing it to just v3/v2_5_turbo here used to silently
        # discard any Gemini tier the caller picked (see profile page's
        # "Suara Percakapan" picker).
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
        # v3 model consumes the tagged variant; everything else uses plain.
        spoken_text = plain_text
        if adapted_voice.get("tts_model") == "v3":
            tagged = str(adapted_voice.get("speech_response_tags") or "").strip()
            if tagged:
                spoken_text = tagged

        if mode == "openai_tts1":
            # Explicit "force OpenAI" sentinel -- skip ElevenLabs/Gemini
            # entirely rather than running the normal fallback chain.
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
            # Same ElevenLabs -> (Gemini/OpenAI, ordered by LLM_PROVIDER)
            # chain the in-turn chat voice reply uses -- this endpoint
            # used to hardcode ElevenLabs -> OpenAI only, so it never
            # reached Gemini even when the caller picked a Gemini voice
            # character (e.g. a raw prebuilt voice name like "Sulafat").
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
        """Transcribe one audio clip without running a full chat turn.

        Used by the chat composer's mic button: the user reviews/edits the
        transcript in the textarea before it becomes a real message, so this
        must NOT invoke the LLM or persist anything — just STT. Mirrors the
        stateless-throwaway-state pattern used by `synthesize_speech` above,
        driving `speech_to_text_node` directly instead of the full graph.
        """
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
        """Stream tokens and a final response from the production graph."""
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
                    # Only stream tokens from user-facing nodes. Internal
                    # nodes (judges, classifiers, summarisers, the speech
                    # adapter, guardrail rewriter, KG extractor) also emit
                    # on_chat_model_stream events — without this guard their
                    # raw JSON/intermediate text leaks into the subtitle.
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
        """Persist a nicer Mermaid PNG of the compiled LangGraph.

        This is intended for development/debugging.
        """
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

        # Mermaid frontmatter config. Unknown keys are ignored by Mermaid,
        # so this stays compatible across Mermaid versions.
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
        """Resolve dependencies and compile the graph. Runs once."""
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
        """Build the LLM_PROVIDER-preferred transcription provider, or None
        when neither OpenAI nor Gemini is configured at all.

        STT is optional, exactly like the two TTS providers below --
        text-only chat never touches it. This used to unconditionally
        build an OpenAI provider and crashed the ONE-TIME lazy graph
        build (_build_graph_once) for every request, text or voice,
        whenever OPENAI_API_KEY was unset (e.g. production running
        LLM_PROVIDER=gemini with no OpenAI key). The crash surfaced
        after the SSE response had already started (200 OK sent, then
        the stream died), which is what the Go client saw as "agentic
        read stream: unexpected EOF".

        Only returns the PRIMARY provider for logging/diagnostics --
        speech_to_text_node computes its own LLM_PROVIDER-ordered
        primary/fallback pair independently (see
        _default_stt_providers there) whenever this returns None, so
        transcription still works even when this constructs nothing.
        """
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
        # Preferred provider's key is missing but the other is configured.
        return GeminiTranscriptionProvider() if has_gemini else OpenAITranscriptionProvider()

    @staticmethod
    def _build_tts_providers() -> tuple[Any | None, Any | None]:
        """Build available TTS providers (ElevenLabs tier 0, OpenAI as one
        of the two LLM_PROVIDER-ordered fallback tiers -- see
        text_to_speech_node for the actual ordering logic; the Gemini
        client is always built lazily via its own internal default)."""
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
        """Bridge the production context_builder to the node signature."""
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
        """Normalize raw dict input into the typed request schema."""
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
        """Materialize a fresh ConversationState from the request."""
        request = cls._coerce_request(request)
        state = empty_conversation_state(
            user_id=request.user_id,
            session_id=request.session_id,
            language_pref=request.language_pref,
        )
        state["messages"] = [m.model_dump() for m in request.messages]
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
        # Avoid stale PHQ-9 state on the first turn of a new session.
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
        """Serialize the post-graph state into the response schema."""
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

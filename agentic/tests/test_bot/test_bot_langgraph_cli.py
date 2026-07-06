"""Real LangGraph CLI for the Companionship Chatbot."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

# Optional dotenv so the user's .env is loaded without manual export.
try:  # pragma: no cover
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv()
except Exception:
    pass

# testing logging disable
# logging.disable(logging.CRITICAL)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "WARNING"),
    # level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
log = logging.getLogger("test_bot_cli")



async def _build_pg_pool() -> Any | None:
    if not os.getenv("PG_PASSWORD"):
        return None
    try:
        import asyncpg  # type: ignore[import-not-found]

        return await asyncpg.create_pool(
            host=os.getenv("PG_HOST", "localhost"),
            port=int(os.getenv("PG_PORT", "5432")),
            user=os.getenv("PG_USER", "companion"),
            password=os.getenv("PG_PASSWORD"),
            database=os.getenv("PG_DATABASE", "companion_chatbot"),
            min_size=int(os.getenv("PG_POOL_MIN_SIZE", "1")),
            max_size=int(os.getenv("PG_POOL_MAX_SIZE", "10")),
        )
    except Exception as exc:
        log.warning("postgres unavailable: %s", exc)
        return None


async def _build_neo4j() -> Any | None:
    if not os.getenv("NEO4J_PASSWORD"):
        return None
    try:
        from neo4j import AsyncGraphDatabase  # type: ignore[import-not-found]

        driver = AsyncGraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD"),
            ),
            max_connection_pool_size=int(os.getenv("NEO4J_POOL_SIZE", "20")),
        )
        await driver.verify_connectivity()
        return driver
    except Exception as exc:
        log.warning("neo4j unavailable: %s", exc)
        return None


async def _build_deps() -> dict[str, Any]:
    print("Bootstrapping deps...")
    pg_pool = await _build_pg_pool()
    neo4j_driver = await _build_neo4j()

    print(f"  postgres : {'OK' if pg_pool else 'unavailable'}")
    print(f"  neo4j    : {'OK' if neo4j_driver else 'unavailable'}")
    print(f"  openai   : {'OK' if os.getenv('OPENAI_API_KEY') else 'missing key'}")
    print(f"  11labs   : {'OK' if os.getenv('ELEVENLABS_API_KEY') else 'missing key'}")

    from agentic.agent.audit.guardrail_events import (
        NullGuardrailLogger,
        PostgresGuardrailLogger,
    )
    from agentic.agent.session.activity_repo import (
        InMemorySessionActivityRepository,
        PostgresSessionActivityRepository,
    )
    from agentic.memory.assessment_repo import AssessmentRepository

    audit_logger = (
        PostgresGuardrailLogger(pg_pool=pg_pool) if pg_pool
        else NullGuardrailLogger()
    )
    activity_repo = (
        PostgresSessionActivityRepository(pg_pool=pg_pool) if pg_pool
        else InMemorySessionActivityRepository()
    )
    assessment_repo = AssessmentRepository(
        pg_pool=pg_pool, neo4j_driver=neo4j_driver,
    )

    # The production context_builder uses agentic.memory.neo4j_client.get_client()
    # (module-level singleton). Initialize it here so retrieval signals can
    # query Neo4j during CLI runs.
    if neo4j_driver is not None:
        try:
            from agentic.memory.neo4j_client import init_client

            await init_client()
        except Exception as exc:
            log.warning("neo4j_client init failed: %s", exc)

    from agentic.config.voices import load_voice_catalog

    catalog = load_voice_catalog(force_reload=True)

    from agentic.agent.nodes.speech_to_text import OpenAITranscriptionProvider
    stt_provider = (
        OpenAITranscriptionProvider() if os.getenv("OPENAI_API_KEY") else None
    )

    from agentic.agent.nodes.text_to_speech import (
        ElevenLabsClient,
        OpenAITTSClient,
    )
    elevenlabs = (
        ElevenLabsClient() if os.getenv("ELEVENLABS_API_KEY") else None
    )
    openai_tts = OpenAITTSClient() if os.getenv("OPENAI_API_KEY") else None

    if neo4j_driver is None or pg_pool is None:
        os.environ["AGENTIC_DISABLE_CONTEXT_BUILDER"] = "1"
        context_builder = None
    else:
        context_builder = _wrap_context_builder()

    return {
        "pg_pool": pg_pool,
        "neo4j_driver": neo4j_driver,
        "audit_logger": audit_logger,
        "activity_repo": activity_repo,
        "assessment_repo": assessment_repo,
        "catalog": catalog,
        "stt_provider": stt_provider,
        "elevenlabs": elevenlabs,
        "openai_tts": openai_tts,
        "context_builder": context_builder,
    }


async def _ensure_user_exists(
    *,
    pg_pool: Any,
    user_id: str,
    preferred_language: str,
    display_name: str = "CLI User",
) -> None:
    """Ensure the CLI user exists so FK inserts (e.g. guardrail_events) succeed.

    The backend schema requires users.email, users.display_name, users.password_hash.
    For local CLI runs we create a deterministic, non-sensitive placeholder user.
    """
    if not user_id:
        return

    # Deterministic email avoids collisions across runs while remaining unique.
    email = f"cli+{user_id}@local.test"
    # users.password_hash is CHAR(60) (bcrypt). For FK purposes we only need a
    # non-null 60-char string.
    password_hash = "x" * 60

    try:
        async with pg_pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE id = $1",
                user_id,
            )
            if exists:
                return
            await conn.execute(
                """
                INSERT INTO users (
                    id, email, display_name, password_hash, preferred_language
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO NOTHING
                """,
                user_id,
                email,
                display_name,
                password_hash,
                (preferred_language or "id")[:2],
            )
    except Exception as exc:
        # Keep CLI resilient; missing user will only degrade DB-backed telemetry.
        log.warning("could not ensure user exists in postgres: %s", exc)


def _wrap_context_builder():
    """Bridge the production context_builder to the node's signature."""
    async def _bridge(*, user_id, session_id, query, language):
        try:
            from agentic.memory.context_builder import build_context
            from agentic.memory.pg_vector import embed_text

            del session_id, language  # reserved for future builder upgrades
            query_embedding = None
            if query and query.strip():
                try:
                    query_embedding = await embed_text(query)
                except Exception:
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
            log.warning("context_builder bridge failed: %s", exc)
            return ""

    return _bridge


def _build_finalizer():
    """Real session finalizer with summarizer + extractor LLMs."""
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from agentic.agent.session.finalizer import SessionFinalizer
        from agentic.config.llm_models import (
            KG_EXTRACTOR,
            SESSION_SUMMARIZER,
            build_llm,
        )

        summarizer_llm = build_llm(SESSION_SUMMARIZER)
        extractor_llm = build_llm(KG_EXTRACTOR)

        try:
            from langchain_core.messages import (  # type: ignore[import-not-found]
                HumanMessage,
                SystemMessage,
            )
        except Exception:  # pragma: no cover
            from dataclasses import dataclass

            @dataclass
            class SystemMessage:
                content: str
                type: str = "system"

            @dataclass
            class HumanMessage:
                content: str
                type: str = "human"

        async def _loader(*, session_id, user_id):
            return []

        async def _summarize(*, transcript, language):
            ai = await summarizer_llm.ainvoke([
                SystemMessage(content=SESSION_SUMMARIZER.system_prompt),
                HumanMessage(content=transcript),
            ])
            return ai.content if isinstance(ai.content, str) else str(ai.content)

        async def _extract(*, message, user_id, session_id, language):
            ai = await extractor_llm.ainvoke([
                SystemMessage(content=KG_EXTRACTOR.system_prompt),
                HumanMessage(content=message),
            ])
            raw = ai.content if isinstance(ai.content, str) else str(ai.content)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}

        async def _writer(*, user_id, session_id, summary, extracted, language):
            print(
                f"  [finalize] session={session_id} "
                f"summary_chars={len(summary)} extracted={len(extracted)}"
            )

        return SessionFinalizer(
            history_loader=_loader,
            summarizer=_summarize,
            extractor=_extract,
            kg_writer=_writer,
        )
    except Exception as exc:
        log.warning("finalizer build failed: %s", exc)
        return None



HELP_TEXT = """\
Commands:
  /help                       this help
  /quit | /exit               exit
  /voice on | off             toggle voice output (TTS)
  /audio <path>               attach wav/mp3/m4a as next user turn
  /lang id | en               override resolved_language
  /reset                      new session id
    /context                    print current kg_context block
  /state                      abbreviated state dump
  /sweep                      run session sweeper once
  /play                       open last bot audio with system player
"""


def _short_state(state: dict[str, Any]) -> str:
    voice = state.get("voice_state") or {}
    phq9 = state.get("phq9_state") or {}
    kg_context = (state.get("kg_context") or "")
    summary = {
        "session_turn": state.get("session_turn"),
        "resolved_language": state.get("resolved_language"),
        "safety_flag": state.get("safety_flag"),
        "input_guardrail": (state.get("input_guardrail") or {}).get("decision"),
        "phq9.phase": phq9.get("phase"),
        "phq9.active_item": phq9.get("active_item"),
        "phq9.route_to_crisis_after": phq9.get("route_to_crisis_after"),
        "cbt_node_active": state.get("cbt_node_active"),
        "voice.modality": voice.get("output_modality"),
        "voice.tts_provider": voice.get("tts_provider"),
        "voice.tts_streaming": voice.get("tts_streaming"),
        "kg_context_chars": len(kg_context),
        "messages_in_history": len(state.get("messages") or []),
    }
    return json.dumps(summary, indent=2, default=str, ensure_ascii=False)



def _wrap_audio_bytes(path: Path) -> tuple[Any, str]:
    """Return an OpenAI transcription-friendly file-like + mime."""
    suffix = path.suffix.lower().lstrip(".")
    mime = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
    }.get(suffix, "audio/mpeg")
    data = path.read_bytes()
    buf = io.BytesIO(data)
    buf.name = path.name  # OpenAI SDK looks at .name to pick the decoder
    return buf, mime


async def _consume_audio_blob(blob: Any) -> bytes:
    """Drain a streaming generator (or return raw bytes)."""
    if isinstance(blob, (bytes, bytearray)):
        return bytes(blob)
    chunks: list[bytes] = []
    if hasattr(blob, "__aiter__"):
        async for ch in blob:
            chunks.append(bytes(ch))
        return b"".join(chunks)
    if hasattr(blob, "__iter__"):
        try:
            for ch in blob:
                chunks.append(bytes(ch))
            return b"".join(chunks)
        except TypeError:
            return b""
    return b""


def _save_audio(audio_bytes: bytes, *, suffix: str = ".mp3") -> Path:
    fd, raw = tempfile.mkstemp(suffix=suffix, prefix="bot_tts_")
    os.close(fd)
    p = Path(raw)
    p.write_bytes(audio_bytes)
    return p


def _open_with_player(path: Path) -> bool:
    """Best-effort system player open."""
    if sys.platform == "darwin":
        cmd = ["afplay", str(path)]
    elif sys.platform.startswith("linux"):
        cmd = ["xdg-open", str(path)]
    elif sys.platform.startswith("win"):
        cmd = ["cmd.exe", "/c", "start", "", str(path)]
    else:
        return False
    if shutil.which(cmd[0]) is None:
        return False
    try:
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False



async def _main() -> int:
    # CLI identity: set CLI_USER_ID to use a stable user across runs.
    # Must be established early so Postgres-backed telemetry (guardrail_events)
    # doesn't trip FK constraints during graph bootstrap.
    user_id = os.getenv("CLI_USER_ID", "11111111-1111-1111-1111-111111111111")
    session_id = str(uuid.uuid4())

    deps = await _build_deps()

    if deps["pg_pool"] is not None:
        await _ensure_user_exists(
            pg_pool=deps["pg_pool"],
            user_id=user_id,
            preferred_language=os.getenv("DEFAULT_USER_LANGUAGE", "id"),
        )

    try:
        from agentic.agent.graph import build_graph
        from agentic.config.llm_models import (
            GUARDRAIL_REWRITE,
            PHQ9_FEEDBACK,
            PHQ9_JUDGE,
            RESPONSE_GENERATOR,
            SPEECH_ADAPTER,
            SPEECH_ADAPTER_V3,
            CBT_JUDGE,
            build_llm,
        )

        # Real LLM clients (LangChain ChatOpenAI). These require provider
        # credentials (e.g. OPENAI_API_KEY) for successful invocation.
        response_llm = build_llm(RESPONSE_GENERATOR)
        phq9_judge_llm = build_llm(PHQ9_JUDGE)
        feedback_llm = build_llm(PHQ9_FEEDBACK)
        rewrite_llm = build_llm(GUARDRAIL_REWRITE)
        speech_adapter_llm_v25 = build_llm(SPEECH_ADAPTER)
        speech_adapter_llm_v3 = build_llm(SPEECH_ADAPTER_V3)
        cbt_judge_llm = build_llm(CBT_JUDGE)

        graph = build_graph(
            assessment_repo=deps["assessment_repo"],
            audit_logger=deps["audit_logger"],
            activity_repo=deps["activity_repo"],
            voice_catalog=deps["catalog"],
            stt_provider=deps["stt_provider"],
            elevenlabs_tts=deps["elevenlabs"],
            openai_tts=deps["openai_tts"],
            context_builder=deps["context_builder"],
            response_llm=response_llm,
            scorer_llm=phq9_judge_llm,
            phq9_judge_llm=phq9_judge_llm,
            feedback_llm=feedback_llm,
            rewrite_llm=rewrite_llm,
            speech_adapter_llm_v25=speech_adapter_llm_v25,
            speech_adapter_llm_v3=speech_adapter_llm_v3,
            cbt_judge_llm=cbt_judge_llm,
        )
    except Exception as exc:
        print(f"\n[fatal] could not build graph: {exc}")
        print(
            "Hint: ensure 'langgraph' is installed in the venv "
            "(pip install langgraph)."
        )
        return 1

    from agentic.agent.session.sweeper import SessionSweeper, SweeperConfig
    from agentic.agent.state import empty_conversation_state

    finalizer = _build_finalizer()
    sweeper: SessionSweeper | None = None
    if finalizer is not None:
        sweeper = SessionSweeper(
            repo=deps["activity_repo"],
            finalizer=finalizer,
            config=SweeperConfig(idle_minutes=30, batch_limit=10, max_attempts=2),
            audit=deps["audit_logger"],
        )

    state = empty_conversation_state(
        user_id=user_id,
        session_id=session_id,
        language_pref=os.getenv("DEFAULT_USER_LANGUAGE", "id"),
    )
    state["resolved_language"] = state["language_pref"]

    last_audio_path: Path | None = None
    voice_default_off = True

    print("\n" + "=" * 60)
    print(" Companionship Chatbot - real LangGraph CLI")
    print(f" user_id    = {user_id}")
    print(f" session_id = {session_id}")
    print(" Type /help for commands, /quit to exit")
    print("=" * 60 + "\n")

    while True:
        try:
            print("\n" + "=" * 60)
            user_text = input("you> ").strip()
            print("=" * 60 + "\n")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue

        if user_text.startswith("/"):
            parts = user_text.split()
            head = parts[0]
            rest = parts[1:]
            if head in ("/quit", "/exit"):
                break
            if head == "/help":
                print(HELP_TEXT)
                continue
            if head == "/context":
                block = (state.get("kg_context") or "").strip()
                print(block if block else "(kg_context empty)")
                continue
            if head == "/state":
                print(_short_state(state))
                continue
            if head == "/voice" and rest:
                on = rest[0].lower() == "on"
                voice_default_off = not on
                voice = dict(state.get("voice_state") or {})
                voice["output_modality"] = "voice" if on else "text"
                state["voice_state"] = voice
                print(f"  voice mode: {'on' if on else 'off'}")
                continue
            if head == "/lang" and rest:
                state["resolved_language"] = rest[0]
                print(f"  resolved_language = {rest[0]}")
                continue
            if head == "/reset":
                user_id = str(uuid.uuid4())
                session_id = str(uuid.uuid4())
                if deps["pg_pool"] is not None:
                    await _ensure_user_exists(
                        pg_pool=deps["pg_pool"],
                        user_id=user_id,
                        preferred_language=os.getenv("DEFAULT_USER_LANGUAGE", "id"),
                    )
                state = empty_conversation_state(
                    user_id=user_id,
                    session_id=session_id,
                    language_pref=os.getenv("DEFAULT_USER_LANGUAGE", "id"),
                )
                state["resolved_language"] = state["language_pref"]
                last_audio_path = None
                voice_default_off = True
                print(f"  reset to session {session_id[:8]}")
                continue
            if head == "/sweep":
                if sweeper is None:
                    print("  sweeper unavailable (missing OPENAI_API_KEY?)")
                    continue
                handled = await sweeper.run_once()
                print(f"  sweeper handled {len(handled)} session(s)")
                continue
            if head == "/audio" and rest:
                path = Path(" ".join(rest)).expanduser()
                if not path.is_file():
                    print(f"  audio file not found: {path}")
                    continue
                buf, mime = _wrap_audio_bytes(path)
                voice = dict(state.get("voice_state") or {})
                voice["audio_input"] = buf
                voice["audio_input_mime"] = mime
                voice["output_modality"] = "voice"
                state["voice_state"] = voice
                voice_default_off = False
                print(
                    f"  attached audio: {path.name} "
                    f"({len(path.read_bytes())} bytes)"
                )
                user_text = ""  # let the turn run with the attached audio
            elif head == "/play":
                if last_audio_path and last_audio_path.exists():
                    if _open_with_player(last_audio_path):
                        print(f"  launched: {last_audio_path}")
                    else:
                        print(
                            f"  no system player; file is at {last_audio_path}"
                        )
                else:
                    print("  no audio output yet")
                continue
            else:
                print("  unknown command. /help for list")
                continue

        # Build a turn-scoped state and invoke the graph.
        turn_state = dict(state)
        if not (turn_state.get("voice_state") or {}).get("audio_input"):
            turn_state["current_message"] = user_text
            voice = dict(turn_state.get("voice_state") or {})
            voice["output_modality"] = "text" if voice_default_off else "voice"
            turn_state["voice_state"] = voice

        try:
            new_state = await graph.ainvoke(turn_state)
        except Exception as exc:
            log.exception("turn failed: %s", exc)
            print(f"  [error] {exc}")
            continue

        state.update(new_state)

        # Clear consumed audio_input so the next turn does not re-feed it.
        if state.get("voice_state"):
            voice = dict(state["voice_state"])
            voice["audio_input"] = None
            voice["audio_input_mime"] = None
            state["voice_state"] = voice

        reply = state.get("final_response") or state.get("response_draft") or ""
        print("\n" + "=" * 60)
        print(f"\nbot> {reply}")
        print("=" * 60 + "\n")

        voice = state.get("voice_state") or {}
        blob = voice.get("audio_output_blob")
        if blob is not None:
            try:
                audio_bytes = await _consume_audio_blob(blob)
                if audio_bytes:
                    last_audio_path = _save_audio(audio_bytes)
                    print(
                        f"  [audio: {voice.get('tts_provider')} "
                        f"{len(audio_bytes)} bytes -> {last_audio_path}]"
                    )
            except Exception as exc:
                log.warning("could not save audio: %s", exc)

    if deps["pg_pool"] is not None:
        try:
            await deps["pg_pool"].close()
        except Exception:
            pass
    if deps["neo4j_driver"] is not None:
        try:
            await deps["neo4j_driver"].close()
        except Exception:
            pass

    try:
        from agentic.memory.neo4j_client import close_client

        await close_client()
    except Exception:
        pass
    return 0


def main() -> int:
    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())

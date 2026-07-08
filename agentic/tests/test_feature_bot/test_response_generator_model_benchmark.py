"""bench manual OpenAI models"""

from __future__ import annotations

import copy
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from agentic.agent.state import ConversationState
from agentic.config.llm_models import LLMSpec, RESPONSE_GENERATOR
from agentic.gateway.model import ChatTurnRequest
from agentic.gateway.service import chat_graph as chat_graph_module
from agentic.gateway.service.chat_graph import ChatGraphService
from agentic.memory.neo4j_client import close_client, init_client
from agentic.memory.pg_vector.client import close_pool, get_pool


USER_ID = "6aca3b8b-ddcf-4428-824e-997f921d28d3"
ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = ROOT / "agentic" / "tmp" / "response_generator_model_benchmark"
MODEL_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("GPT 5.5", "gpt-5.5"),
    ("GPT 5.4", "gpt-5.4"),
    ("GPT 5.4-mini", "gpt-5.4-mini"),
    ("GPT 5.4-nano", "gpt-5.4-nano"),
    ("GPT 4.1-mini", "gpt-4.1-mini"),
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _slug(value: str) -> str:
    return (
        value.lower()
        .replace(" ", "_")
        .replace(".", "_")
        .replace("-", "_")
    )


def _json_default(value: Any) -> str:
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


async def _load_latest_turn(user_id: str) -> dict[str, Any]:
    pool = await get_pool()
    if pool is None:
        pytest.skip("Postgres unavailable. Check PG_* env values.")

    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            """
            SELECT
                id::text AS session_id,
                user_id::text AS user_id,
                channel,
                status,
                turn_count,
                started_at,
                ended_at
            FROM chat_sessions
            WHERE user_id = $1::uuid
            ORDER BY started_at DESC
            LIMIT 1
            """,
            user_id,
        )
        if session is None:
            pytest.fail(f"no chat session found for user_id={user_id}")

        rows = await conn.fetch(
            """
            SELECT
                role,
                content,
                turn_index,
                created_at
            FROM messages
            WHERE session_id = $1::uuid
            ORDER BY turn_index ASC
            """,
            session["session_id"],
        )

    messages = [dict(row) for row in rows]
    if not messages:
        pytest.fail(f"latest session has no messages: {session['session_id']}")

    override_message = os.getenv("AXIS_RESPONSE_MODEL_TEST_MESSAGE", "").strip()
    if override_message:
        current_message = override_message
        history = [
            {"role": row["role"], "content": row["content"], "metadata": {}}
            for row in messages
            if row["role"] in ("user", "assistant", "system")
        ]
        session_turn = len([m for m in history if m["role"] == "user"])
    else:
        current_idx = None
        for idx in range(len(messages) - 1, -1, -1):
            if messages[idx]["role"] == "user":
                current_idx = idx
                break
        if current_idx is None:
            pytest.fail("latest session has no user message to replay")

        current_message = str(messages[current_idx]["content"])
        history = [
            {"role": row["role"], "content": row["content"], "metadata": {}}
            for row in messages[: current_idx + 1]
            if row["role"] in ("user", "assistant", "system")
        ]
        session_turn = len([m for m in history if m["role"] == "user"])

    return {
        "session": dict(session),
        "history": history,
        "current_message": current_message,
        "session_turn": session_turn,
        "raw_message_count": len(messages),
    }


async def _build_realistic_request(
    user_id: str,
) -> tuple[ChatTurnRequest, dict[str, Any]]:
    loaded = await _load_latest_turn(user_id)
    session = loaded["session"]
    request = ChatTurnRequest(
        user_id=user_id,
        session_id=session["session_id"],
        # `set current_msg`
        current_message="apa yang lu tau tentang gua?",
        messages=loaded["history"],
        session_turn=loaded["session_turn"],
        language_pref=os.getenv("AXIS_RESPONSE_MODEL_TEST_LANGUAGE", "id"),
        include_state=True,
    )
    return request, loaded


def _model_spec(model: str) -> LLMSpec:
    return LLMSpec(
        name=f"response_generator_benchmark_{_slug(model)}",
        model=model,
        temperature=RESPONSE_GENERATOR.temperature,
        max_tokens=RESPONSE_GENERATOR.max_tokens,
        prompt_ref=RESPONSE_GENERATOR.prompt_ref,
        timeout_s=float(os.getenv("AXIS_RESPONSE_MODEL_TEST_TIMEOUT", "60")),
    )


async def _run_graph_with_response_model(
    request: ChatTurnRequest,
    model: str,
) -> ConversationState:
    service = ChatGraphService()
    original_spec = chat_graph_module.RESPONSE_GENERATOR
    try:
        chat_graph_module.RESPONSE_GENERATOR = _model_spec(model)
        graph = await service._get_graph()
    finally:
        chat_graph_module.RESPONSE_GENERATOR = original_spec

    state = service._request_to_state(copy.deepcopy(request))
    return await graph.ainvoke(state)


def _write_markdown(
    *,
    path: Path,
    model_label: str,
    model: str,
    elapsed_ms: float | None,
    state: ConversationState,
    loaded: dict[str, Any],
    reply: str | None,
    error: str | None,
) -> None:
    session = loaded["session"]
    payload = {
        "model_label": model_label,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "user_id": state.get("user_id"),
        "session_id": state.get("session_id"),
        "session_status": session.get("status"),
        "session_turn": state.get("session_turn"),
        "raw_message_count": loaded.get("raw_message_count"),
        "history_messages_used": len(state.get("messages") or []),
        "current_message_chars": len(state.get("current_message") or ""),
        "resolved_language": state.get("resolved_language"),
        "kg_context_chars": len(state.get("kg_context") or ""),
        "cbt_node_active": state.get("cbt_node_active"),
        "cbt_directive": state.get("cbt_directive"),
        "safety_flag": state.get("safety_flag"),
        "crisis_tier": state.get("crisis_tier"),
        "final_response_chars": len(state.get("final_response") or ""),
        "response_draft_chars": len(state.get("response_draft") or ""),
        "graph_path": "ChatGraphService._get_graph -> graph.ainvoke",
        "error": error,
    }
    content = [
        f"# {model_label}",
        "",
        "## Metadata",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        "```",
        "",
        "## Current User Message",
        "",
        state.get("current_message") or "",
        "",
        "## Response",
        "",
        reply or "",
    ]
    if error:
        content.extend(["", "## Error", "", error])
    path.write_text("\n".join(content).strip() + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_response_generator_model_benchmark_outputs_markdown() -> None:
    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / "agentic" / ".env")

    if os.getenv("AXIS_RUN_RESPONSE_MODEL_BENCHMARK") != "1":
        pytest.skip(
            "Set AXIS_RUN_RESPONSE_MODEL_BENCHMARK=1 to run this real DB/LLM benchmark."
        )

    await init_client()
    try:
        base_request, loaded = await _build_realistic_request(USER_ID)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        index_lines = [
            "# Response Generator Model Benchmark",
            "",
            f"- User ID: `{USER_ID}`",
            f"- Session ID: `{base_request.session_id}`",
            f"- Current message chars: `{len(base_request.current_message or '')}`",
            f"- History messages used: `{len(base_request.messages)}`",
            "- Graph path: `ChatGraphService._get_graph -> graph.ainvoke`",
            "",
            "## Files",
            "",
        ]

        for label, model in MODEL_CANDIDATES:
            state = None
            output_path = OUTPUT_DIR / f"{_slug(model)}.md"
            started = time.perf_counter()
            reply = None
            error = None
            elapsed_ms = None
            try:
                state = await _run_graph_with_response_model(base_request, model)
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                reply = state.get("final_response") or state.get("response_draft") or ""
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                error = f"{type(exc).__name__}: {exc}"
                state = ChatGraphService._request_to_state(copy.deepcopy(base_request))

            _write_markdown(
                path=output_path,
                model_label=label,
                model=model,
                elapsed_ms=elapsed_ms,
                state=state,
                loaded=loaded,
                reply=reply,
                error=error,
            )
            status = "error" if error else "ok"
            index_lines.append(f"- [{label}]({output_path.name}) - `{status}`")

        index_path = OUTPUT_DIR / "README.md"
        index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
        print(f"\nResponse benchmark output: {OUTPUT_DIR}")

        assert index_path.exists()
        assert all(
            (OUTPUT_DIR / f"{_slug(model)}.md").exists()
            for _, model in MODEL_CANDIDATES
        )
    finally:
        await close_client()
        await close_pool()

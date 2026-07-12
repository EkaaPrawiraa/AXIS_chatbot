#!/usr/bin/env python3
"""Run controlled evaluation scenarios."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from dotenv import load_dotenv

from chatbot import BASELINE_SYSTEM_PROMPT, baseline_turn
from config import CONFIG, REPO_ROOT, EvaluationConfig
from metrics import aggregate_scores, score_transcript
from provenance import build_manifest, write_json
from scenarios import Scenario, select_scenarios


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ensure_user_and_session(config: EvaluationConfig, user_id: str, session_id: str) -> None:
    with psycopg2.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE id = %s", (user_id,))
            if cursor.fetchone() is None:
                raise RuntimeError(
                    f"Evaluation user {user_id} is missing. Run "
                    "`python evaluation_pipeline/seeder.py --confirm-reset` first."
                )
            cursor.execute(
                """
                INSERT INTO chat_sessions (id, user_id, channel, status, title)
                VALUES (%s, %s, 'text', 'active', %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (session_id, user_id, "Controlled evaluation"),
            )


def _cleanup_session(config: EvaluationConfig, session_id: str) -> None:
    with psycopg2.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM assessments WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM session_activity WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM guardrail_events WHERE session_id = %s", (session_id,))
            cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    if config.neo4j_password:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_username, config.neo4j_password),
        )
        try:
            with driver.session(database=config.neo4j_database) as session:
                session.run(
                    """
                    OPTIONAL MATCH (s:Session {id: $session_id})
                    OPTIONAL MATCH (s)-[:PRODUCED_ASSESSMENT]->(a:Assessment)
                    DETACH DELETE a, s
                    """,
                    session_id=session_id,
                ).consume()
        finally:
            driver.close()


def _write_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _write_transcript(
    path: Path,
    *,
    system: str,
    scenario: Scenario,
    repetition: int,
    records: list[dict[str, Any]],
) -> None:
    lines = [
        f"# {system.upper()} — {scenario.title}",
        "",
        f"- Scenario: `{scenario.id}`",
        f"- Rumusan masalah: `{scenario.research_question}`",
        f"- Kondisi memori: `{scenario.memory_condition}`",
        f"- Repetition: `{repetition}`",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## Turn {record['turn']}",
                "",
                f"**User:** {record['user']}",
                "",
                f"**{system.upper()}:** {record.get('assistant') or '[ERROR]'}",
                "",
                f"Latency: `{record.get('latency_ms')} ms`",
                "",
            ]
        )
        if record.get("error"):
            lines.extend([f"Error: `{record['error']}`", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def _axis_service(config: EvaluationConfig) -> Any:
    agentic_dir = REPO_ROOT / "agentic"
    load_dotenv(agentic_dir / ".env", override=False)
    os.environ["LLM_PROVIDER"] = config.axis_provider
    if str(agentic_dir) not in sys.path:
        sys.path.insert(0, str(agentic_dir))
    from agentic.gateway.service.chat_graph import ChatGraphService

    ChatGraphService.draw_graph_image = lambda self: None
    service = ChatGraphService()
    await service._get_graph()
    return service


async def _run_axis(
    *,
    service: Any,
    config: EvaluationConfig,
    scenario: Scenario,
    repetition: int,
    raw_path: Path,
) -> list[dict[str, Any]]:
    from agentic.gateway.model import ChatMessage, ChatTurnRequest

    session_id = str(uuid.uuid4())
    _ensure_user_and_session(config, scenario.user_id, session_id)
    history: list[ChatMessage] = []
    records: list[dict[str, Any]] = []
    phq9_state: dict[str, Any] | None = None
    cbt_state: dict[str, Any] | None = None
    try:
        for index, user_message in enumerate(scenario.turns, start=1):
            history.append(ChatMessage(role="user", content=user_message))
            request = ChatTurnRequest(
                user_id=scenario.user_id,
                session_id=session_id,
                current_message=user_message,
                messages=history,
                session_turn=index,
                language_pref="id",
                phq9_state=phq9_state,
                cbt_state=cbt_state,
                include_state=True,
                confession_mode=False,
            )
            started = time.perf_counter()
            try:
                response = await service.invoke(request)
                latency_ms = int((time.perf_counter() - started) * 1000)
                reply = response.reply
                phq9_state = response.phq9_state
                cbt_state = response.cbt_state
                record = {
                    "system": "axis",
                    "scenario_id": scenario.id,
                    "research_question": scenario.research_question,
                    "repetition": repetition,
                    "turn": index,
                    "session_id": session_id,
                    "user": user_message,
                    "assistant": reply,
                    "latency_ms": latency_ms,
                    "resolved_language": response.resolved_language,
                    "safety_flag": response.safety_flag,
                    "crisis_tier": response.crisis_tier,
                    "cbt_node_active": response.cbt_node_active,
                    "phq9_state": response.phq9_state,
                    "kg_context": response.kg_context,
                    "retrieved_memories": [],
                    "error": None,
                }
                history.append(ChatMessage(role="assistant", content=reply))
            except Exception as exc:
                record = {
                    "system": "axis",
                    "scenario_id": scenario.id,
                    "research_question": scenario.research_question,
                    "repetition": repetition,
                    "turn": index,
                    "session_id": session_id,
                    "user": user_message,
                    "assistant": "",
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            records.append(record)
            _write_jsonl(raw_path, record)
            if record.get("error"):
                break
    finally:
        _cleanup_session(config, session_id)
    return records


async def _run_baseline(
    *,
    config: EvaluationConfig,
    scenario: Scenario,
    repetition: int,
    raw_path: Path,
) -> list[dict[str, Any]]:
    history: list[dict[str, str]] = []
    records: list[dict[str, Any]] = []
    provider_seed = config.random_seed + repetition
    for index, user_message in enumerate(scenario.turns, start=1):
        history.append({"role": "user", "content": user_message})
        try:
            result = await asyncio.to_thread(
                baseline_turn,
                user_id=scenario.user_id,
                user_message=user_message,
                history=history,
                config=config,
                repetition_seed=provider_seed,
            )
            record = {
                "system": "baseline",
                "scenario_id": scenario.id,
                "research_question": scenario.research_question,
                "repetition": repetition,
                "turn": index,
                "session_id": None,
                "user": user_message,
                "assistant": result.reply,
                "latency_ms": result.latency_ms,
                "model": result.model,
                "usage": result.usage,
                "retrieved_memories": result.retrieved_memories,
                "system_prompt": result.system_prompt,
                "safety_flag": None,
                "crisis_tier": None,
                "cbt_node_active": None,
                "phq9_state": None,
                "kg_context": None,
                "error": None,
            }
            history.append({"role": "assistant", "content": result.reply})
        except Exception as exc:
            record = {
                "system": "baseline",
                "scenario_id": scenario.id,
                "research_question": scenario.research_question,
                "repetition": repetition,
                "turn": index,
                "user": user_message,
                "assistant": "",
                "latency_ms": None,
                "retrieved_memories": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        records.append(record)
        _write_jsonl(raw_path, record)
        if record.get("error"):
            break
    return records


def _write_summary(path: Path, *, manifest: dict[str, Any], scores: list[dict[str, Any]], aggregate: dict[str, Any]) -> None:
    systems = manifest["systems"]
    if systems == ["axis"]:
        boundary = (
            "Run ini memvalidasi perilaku AXIS pada input terkontrol. Run ini "
            "tidak membandingkan AXIS dengan baseline."
        )
    elif systems == ["baseline"]:
        boundary = (
            "Run ini memvalidasi baseline vector-RAG saja. Tidak ada inferensi "
            "keunggulan relatif tanpa run AXIS pada skenario yang sama."
        )
    else:
        boundary = (
            "Run ini membandingkan AXIS sebagai sistem lengkap dengan baseline "
            "vector-RAG pada input yang sama."
        )
    lines = [
        "# Ringkasan Evaluasi Terkontrol",
        "",
        f"Run ID: `{manifest['run_id']}`",
        f"Protocol: `{manifest['protocol']}`",
        f"Git commit: `{manifest['source']['git_commit']}`",
        f"Dirty worktree: `{manifest['source']['git_dirty']}`",
        "",
        "## Batas Interpretasi",
        "",
        boundary,
        "",
        "## Agregat",
        "",
        "| Sistem / skenario | Pengulangan | Tanpa error | Rerata latensi (ms) | Rerata Jaccard berurutan | Klaim klinis | Ekspektasi safety terpenuhi | PHQ item 9 terpenuhi |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, value in sorted(aggregate.items()):
        lines.append(
            f"| {key} | {value['repetitions']} | {value['successful_repetitions']} | "
            f"{value['mean_latency_ms']} | {value['mean_adjacent_response_jaccard']} | "
            f"{value['clinical_claims']} | {value['safety_expectation_met']} | "
            f"{value['phq9_item9_expectation_met']} |"
        )
    lines.extend(
        [
            "",
            "## Per Transkrip",
            "",
            "Metrik deterministik rinci tersimpan di `metrics.json`; data mentah setiap "
            "giliran tersimpan di `raw.jsonl`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(args: argparse.Namespace, config: EvaluationConfig = CONFIG) -> Path:
    systems = _parse_csv(args.systems)
    unknown = set(systems) - {"axis", "baseline"}
    if unknown:
        raise ValueError(f"Unknown system(s): {', '.join(sorted(unknown))}")
    scenarios = select_scenarios(_parse_csv(args.scenarios))
    repetitions = args.repetitions or config.repetitions
    run_id = args.run_id or _run_id()
    run_dir = config.results_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = build_manifest(
        run_id=run_id,
        config=config,
        systems=systems,
        scenarios=scenarios,
        repetitions=repetitions,
        baseline_prompt=BASELINE_SYSTEM_PROMPT,
    )
    write_json(run_dir / "manifest.json", manifest)
    if args.dry_run:
        return run_dir

    config.validate_for(
        baseline="baseline" in systems,
        axis="axis" in systems,
    )
    random.seed(config.random_seed)
    raw_path = run_dir / "raw.jsonl"
    axis_service = await _axis_service(config) if "axis" in systems else None
    scored: list[dict[str, Any]] = []

    for repetition in range(1, repetitions + 1):
        for scenario in scenarios:
            for system in systems:
                if scenario.scope == "axis_only" and system != "axis":
                    continue
                if system == "axis":
                    records = await _run_axis(
                        service=axis_service,
                        config=config,
                        scenario=scenario,
                        repetition=repetition,
                        raw_path=raw_path,
                    )
                else:
                    records = await _run_baseline(
                        config=config,
                        scenario=scenario,
                        repetition=repetition,
                        raw_path=raw_path,
                    )
                transcript_path = (
                    run_dir
                    / "transcripts"
                    / f"{system}__{scenario.id}__r{repetition}.md"
                )
                _write_transcript(
                    transcript_path,
                    system=system,
                    scenario=scenario,
                    repetition=repetition,
                    records=records,
                )
                scored.append(
                    {
                        "system": system,
                        "scenario_id": scenario.id,
                        "research_question": scenario.research_question,
                        "repetition": repetition,
                        "metrics": score_transcript(records, scenario),
                    }
                )

    aggregate = aggregate_scores(scored)
    write_json(run_dir / "metrics.json", {"transcripts": scored, "aggregate": aggregate})
    _write_summary(run_dir / "SUMMARY.md", manifest=manifest, scores=scored, aggregate=aggregate)
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Controlled AXIS vs vector-RAG baseline evaluation"
    )
    parser.add_argument("--systems", default="axis,baseline")
    parser.add_argument("--scenarios", default="all")
    parser.add_argument("--repetitions", type=int, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write the reproducibility manifest without calling APIs or databases.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_dir = asyncio.run(run(args))
    print(f"Evaluation artifacts: {run_dir}")


if __name__ == "__main__":
    main()

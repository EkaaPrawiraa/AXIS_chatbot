"""RM3 -- node/relation writing accuracy and update correctness via crafted
scenarios with known ground truth, run against the real production session
finalizer and Neo4j (not mocks).

This is deliberately NOT a large statistical gold corpus (no suitable
Indonesian-language knowledge-graph memory dataset exists publicly, see
docs/thesis_latex/evaluasi_v2/rm3_memori/README.md). Instead, each scenario
has a small, hand-verified set of expected nodes/relations, and precision/
recall/macro-F1 are computed directly from what the real extractor+writer
produced against that expectation -- a scenario-and-outcome test technique,
not a corpus-scale benchmark.

Run from repo root after `set -a; source agentic/.env; set +a`:
    .venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_node_writing_and_update_eval.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation_pipeline"))
sys.path.insert(0, str(Path(__file__).parent))

import psycopg2
from judge_utils import load_project_env  # noqa: E402

OUT = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm3_memori" / "node_writing_and_update_results.json"


@dataclass(frozen=True)
class ExpectedNode:
    label: str
    any_keywords: tuple[str, ...]


@dataclass(frozen=True)
class WritingScenario:
    id: str
    seed_message: str
    expected: tuple[ExpectedNode, ...]


@dataclass(frozen=True)
class UpdateScenario:
    id: str
    initial_message: str
    update_message: str
    expected_action: str  # "supersede" | "reappraise" | "replace"


WRITING_SCENARIOS: tuple[WritingScenario, ...] = (
    WritingScenario(
        id="w01_thesis_advisor_anxiety",
        seed_message=(
            "Aku cemas banget mikirin sidang minggu depan, soalnya dosen "
            "pembimbingku suka nanya detail yang susah banget dijawab kalau "
            "aku belum siap."
        ),
        expected=(
            ExpectedNode("Emotion", ("cemas", "khawatir", "takut", "gelisah")),
            ExpectedNode("Subject", ("dosen pembimbing", "dospem", "pembimbing")),
        ),
    ),
    WritingScenario(
        id="w02_negative_self_thought",
        seed_message=(
            "Abis dimarahin dospem soal revisi kemarin, aku jadi mikir aku "
            "emang nggak pantas lulus cepat kayak temen-temen yang lain."
        ),
        expected=(
            ExpectedNode("Thought", ("nggak pantas", "tidak pantas", "gagal", "tidak layak")),
            ExpectedNode("Subject", ("dosen pembimbing", "dospem", "pembimbing")),
        ),
    ),
    WritingScenario(
        id="w03_family_conflict_behavior",
        seed_message=(
            "Kemarin abis ribut sama ibu soal biaya kuliah, aku jadi susah "
            "tidur semalaman mikirin itu terus."
        ),
        expected=(
            ExpectedNode("Subject", ("ibu",)),
            ExpectedNode("Behavior", ("susah tidur", "tidak bisa tidur", "sulit tidur")),
        ),
    ),
    WritingScenario(
        id="w04_organizational_avoidance",
        seed_message=(
            "Aku jadi males banget ikut rapat organisasi kampus minggu ini, "
            "soalnya keseringan bentrok sama jadwal kuliah dan bikin capek."
        ),
        expected=(
            ExpectedNode("Trigger", ("rapat", "organisasi")),
            ExpectedNode("Behavior", ("males", "malas", "menghindar", "skip")),
        ),
    ),
    WritingScenario(
        id="w05_internship_rejection_distortion",
        seed_message=(
            "Abis gagal wawancara magang kemarin, aku ngerasa aku emang nggak "
            "becus ngapa-ngapain, semua usaha aku sia-sia."
        ),
        expected=(
            ExpectedNode("Trigger", ("wawancara", "magang", "gagal")),
            ExpectedNode("Thought", ("nggak becus", "tidak becus", "sia-sia", "gagal")),
        ),
    ),
    WritingScenario(
        id="w06_groupmate_conflict",
        seed_message=(
            "Temen sekelompok aku ngilang pas deadline tugas besar deket "
            "banget, aku jadi kesel dan capek harus nutupin kerjaan dia."
        ),
        expected=(
            ExpectedNode("Subject", ("teman sekelompok", "temen sekelompok", "kelompok")),
            ExpectedNode("Emotion", ("kesel", "kesal", "marah", "capek")),
        ),
    ),
)

UPDATE_SCENARIOS: tuple[UpdateScenario, ...] = (
    UpdateScenario(
        id="u01_advisor_reappraisal",
        initial_message=(
            "Aku ngerasa dosen pembimbingku nggak suka jadi pembimbingku, "
            "soalnya tiap direview kerjaanku pasti banyak banget revisinya."
        ),
        update_message=(
            "Ternyata pas aku tanya langsung, dosen pembimbingku bilang "
            "revisi sebanyak itu wajar dan dia sebenarnya support penuh "
            "sama aku. Aku sadar aku salah paham selama ini."
        ),
        expected_action="reappraise",
    ),
    UpdateScenario(
        id="u02_organization_competence",
        initial_message=(
            "Aku yakin bakal gagal terus kalau pegang tanggung jawab di "
            "organisasi ini, kayaknya aku emang nggak cocok jadi pengurus."
        ),
        update_message=(
            "Setelah program kerja terakhir berjalan sukses berkat aku, aku "
            "sadar ternyata aku cukup kompeten megang tanggung jawab di "
            "organisasi, nggak seburuk yang aku kira dulu."
        ),
        expected_action="reappraise",
    ),
    UpdateScenario(
        id="u03_procrastination_behavior_change",
        initial_message=(
            "Tiap kepikiran skripsi aku langsung nunda-nunda ngerjainnya, "
            "udah jadi kebiasaan banget buat aku."
        ),
        update_message=(
            "Belakangan ini aku udah mulai bisa nyicil ngerjain skripsi "
            "tanpa nunda-nunda lagi, kebiasaan lamaku itu udah mulai "
            "berubah dan aku lebih rajin sekarang."
        ),
        expected_action="replace",
    ),
    UpdateScenario(
        id="u04_family_support_reappraisal",
        initial_message=(
            "Aku ngerasa keluargaku nggak pernah ngedukung pilihan jurusan "
            "aku sama sekali."
        ),
        update_message=(
            "Ternyata pas aku cerita lebih detail ke orang tua soal "
            "jurusanku, mereka sebenarnya dukung banget, cuma selama ini "
            "aku salah menangkap sikap mereka."
        ),
        expected_action="reappraise",
    ),
)


def _ensure_user(user_id: str, database_url: str) -> None:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status) "
                "VALUES (%s, %s, %s, %s, 'id', true, 'active') ON CONFLICT (id) DO NOTHING",
                (user_id, f"rm3_writing_{user_id}@test.com", "RM3 Writing Test", "nopassword"),
            )
            conn.commit()
    finally:
        conn.close()


def _seed_session(user_id: str, session_id: str, message: str, database_url: str) -> None:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_sessions (id, user_id, channel, status, turn_count) VALUES (%s, %s, 'text', 'ended', 1)",
                (session_id, user_id),
            )
            cur.execute(
                "INSERT INTO messages (session_id, user_id, role, content, turn_index) VALUES (%s, %s, 'user', %s, 1)",
                (session_id, user_id, message),
            )
            conn.commit()
    finally:
        conn.close()


def _cleanup_postgres(user_id: str, database_url: str) -> None:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()


async def _cleanup_neo4j(user_id: str) -> None:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    await client.execute_write(
        "MATCH (u:User {id: $user_id})-[*0..2]-(n) DETACH DELETE n",
        {"user_id": user_id},
    )


async def _written_nodes(user_id: str) -> list[dict]:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    rows = await client.execute_read(
        """
        MATCH (u:User {id: $user_id})-[r]->(n)
        WHERE n:Experience OR n:Emotion OR n:Thought OR n:Behavior OR n:Subject OR n:Trigger OR n:Topic
        RETURN labels(n) AS labels, properties(n) AS props
        UNION
        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(:Experience)-[r2]->(n2)
        WHERE n2:Emotion OR n2:Thought OR n2:Behavior OR n2:Subject OR n2:Trigger
        RETURN labels(n2) AS labels, properties(n2) AS props
        """,
        {"user_id": user_id},
    )
    return [{"label": row["labels"][0], "props": row["props"]} for row in rows]


def _node_text(node: dict) -> str:
    props = node["props"]
    for field_name in ("description", "content", "label", "name", "summary"):
        if props.get(field_name):
            return str(props[field_name]).lower()
    return ""


def _score_scenario(expected: tuple[ExpectedNode, ...], written: list[dict]) -> dict:
    relevant_labels = {spec.label for spec in expected}
    candidates = [n for n in written if n["label"] in relevant_labels]
    matched_candidate_ids: set[int] = set()
    tp = 0
    misses = []
    for spec in expected:
        hit = False
        for index, node in enumerate(candidates):
            if node["label"] != spec.label or index in matched_candidate_ids:
                continue
            text = _node_text(node)
            if any(kw in text for kw in spec.any_keywords):
                matched_candidate_ids.add(index)
                hit = True
                break
        if hit:
            tp += 1
        else:
            misses.append(f"{spec.label}:{spec.any_keywords[0]}")
    fp = len(candidates) - len(matched_candidate_ids)
    fn = len(expected) - tp
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "misses": misses,
        "n_written_relevant_label": len(candidates),
    }


async def _run_writing_scenario(scenario: WritingScenario, database_url: str) -> dict:
    from agentic.agent.session.finalizer_factory import build_session_finalizer

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    _ensure_user(user_id, database_url)
    _seed_session(user_id, session_id, scenario.seed_message, database_url)

    finalizer = build_session_finalizer()
    result = await finalizer.finalize(session_id=session_id, user_id=user_id, language="id")
    if result.error:
        _cleanup_postgres(user_id, database_url)
        return {"id": scenario.id, "error": result.error}

    written = await _written_nodes(user_id)
    score = _score_scenario(scenario.expected, written)

    await _cleanup_neo4j(user_id)
    _cleanup_postgres(user_id, database_url)
    return {"id": scenario.id, "extracted_count": result.extracted_count, **score}


async def _relation_action(user_id: str) -> str | None:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    rows = await client.execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT|EXPERIENCED|EXHIBITED]->(n)
        MATCH (n)-[r:SUPERSEDES|REAPPRAISED_AS|REPLACED_BY]-()
        RETURN type(r) AS action
        LIMIT 5
        """,
        {"user_id": user_id},
    )
    if not rows:
        return None
    actions = {row["action"] for row in rows}
    if "REAPPRAISED_AS" in actions:
        return "reappraise"
    if "REPLACED_BY" in actions:
        return "replace"
    if "SUPERSEDES" in actions:
        return "supersede"
    return None


async def _run_update_scenario(scenario: UpdateScenario, database_url: str) -> dict:
    from agentic.agent.session.finalizer_factory import build_session_finalizer

    user_id = str(uuid.uuid4())
    session_1 = str(uuid.uuid4())
    session_2 = str(uuid.uuid4())
    _ensure_user(user_id, database_url)
    _seed_session(user_id, session_1, scenario.initial_message, database_url)

    finalizer = build_session_finalizer()
    r1 = await finalizer.finalize(session_id=session_1, user_id=user_id, language="id")
    if r1.error:
        _cleanup_postgres(user_id, database_url)
        return {"id": scenario.id, "error": f"session1: {r1.error}"}

    _seed_session(user_id, session_2, scenario.update_message, database_url)
    r2 = await finalizer.finalize(session_id=session_2, user_id=user_id, language="id")
    if r2.error:
        await _cleanup_neo4j(user_id)
        _cleanup_postgres(user_id, database_url)
        return {"id": scenario.id, "error": f"session2: {r2.error}"}

    observed_action = await _relation_action(user_id)
    correct = observed_action == scenario.expected_action

    await _cleanup_neo4j(user_id)
    _cleanup_postgres(user_id, database_url)
    return {
        "id": scenario.id,
        "expected_action": scenario.expected_action,
        "observed_action": observed_action,
        "correct": correct,
    }


async def main() -> None:
    load_project_env()
    os.environ["LLM_PROVIDER"] = "gemini"
    from config import DATABASE_URL  # type: ignore  # noqa: E402
    from agentic.memory.neo4j_client import init_client

    await init_client()

    writing_results = []
    for scenario in WRITING_SCENARIOS:
        print(f"[writing] {scenario.id} ...")
        result = await _run_writing_scenario(scenario, DATABASE_URL)
        print(f"  -> {result}")
        writing_results.append(result)

    update_results = []
    for scenario in UPDATE_SCENARIOS:
        print(f"[update] {scenario.id} ...")
        result = await _run_update_scenario(scenario, DATABASE_URL)
        print(f"  -> {result}")
        update_results.append(result)

    valid_writing = [r for r in writing_results if "error" not in r]
    total_tp = sum(r["tp"] for r in valid_writing)
    total_fp = sum(r["fp"] for r in valid_writing)
    total_fn = sum(r["fn"] for r in valid_writing)
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else None
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None

    valid_updates = [r for r in update_results if "error" not in r]
    update_correctness = (
        sum(bool(r["correct"]) for r in valid_updates) / len(valid_updates) if valid_updates else None
    )

    summary = {
        "node_relation_writing": {
            "n_scenarios": len(WRITING_SCENARIOS),
            "n_valid": len(valid_writing),
            "tp": total_tp, "fp": total_fp, "fn": total_fn,
            "precision": precision, "recall": recall, "f1": f1,
        },
        "update_correctness": {
            "n_scenarios": len(UPDATE_SCENARIOS),
            "n_valid": len(valid_updates),
            "update_correctness": update_correctness,
        },
        "limit": (
            "Scenario-and-outcome test technique with hand-verified expected "
            "nodes/relations, not a large statistical gold corpus (no suitable "
            "Indonesian-language KG memory dataset exists publicly). Results are "
            "illustrative of extractor behavior on these specific cases, not a "
            "population-level precision/recall estimate."
        ),
    }
    OUT.write_text(json.dumps({
        "summary": summary,
        "writing_results": writing_results,
        "update_results": update_results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())

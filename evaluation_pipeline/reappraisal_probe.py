"""Real verification that memory lifecycle operations (SUPERSEDES on Thought,
REAPPRAISED_AS on Experience) actually fire across sessions, not just in unit
tests against hand-built input objects. Runs two real sessions through the
real session finalizer: session 1 states a catastrophic thought tied to an
experience, session 2 (after finalize() on session 1, so user_kg_context can
surface the prior thought/experience id) explicitly revises that belief.
Checks Neo4j directly for the resulting relations.

Run from repo root: cd agentic && ../.venv/bin/python -m evaluation_pipeline.reappraisal_probe
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation_pipeline"))


def _load_env(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and (override or key not in os.environ):
            os.environ[key] = value


_load_env(ROOT / ".env")
_load_env(ROOT / "agentic" / ".env", override=True)
_load_env(ROOT / "evaluation_pipeline" / ".env", override=True)

from config import DATABASE_URL  # noqa: E402

SESSION_1_TURNS = [
    "gue takut banget sidang TA bakal gagal total, kayaknya emang bakal berantakan semua, udah kebayang jelek semua di kepala.",
    "gue juga cemas banget abis denger komentar ketus dospem soal draft proposal gue, kayaknya dia kecewa berat sama kerjaan gue.",
]

SESSION_2_TURNS = [
    "eh inget ga waktu itu gue sempet bilang takut sidang bakal gagal total? kemarin gue coba presentasi latihan di depan temen-temen, ternyata lumayan lancar dan mereka kasih masukan positif. jadi sekarang gue mikirnya beda, kayaknya ga akan seburuk yang gue bayangin dulu.",
    "terus soal komentar ketus dospem waktu itu, kalau gue pikir ulang sekarang, kayaknya itu bukan karena dia kecewa sama gue, tapi dianya emang lagi banyak beban kerjaan aja pas hari itu. jadi maknanya beda buat gue sekarang dibanding waktu itu.",
]


def _ensure_user(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status)
                    VALUES (%s, %s, %s, %s, 'id', true, 'active')
                    """,
                    (user_id, f"reappraisal_probe_{user_id}@test.com", "Reappraisal Probe Test", "nopassword"),
                )
            conn.commit()
    finally:
        conn.close()


def _insert_session(user_id: str, session_id: str, turns: list[str]) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_sessions (id, user_id, channel, status, turn_count) VALUES (%s, %s, 'text', 'ended', %s)",
                (session_id, user_id, len(turns)),
            )
            for i, content in enumerate(turns):
                cur.execute(
                    "INSERT INTO messages (session_id, user_id, role, content, turn_index) VALUES (%s, %s, 'user', %s, %s)",
                    (session_id, user_id, content, i + 1),
                )
            conn.commit()
    finally:
        conn.close()


def _cleanup(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM chat_sessions WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
    finally:
        conn.close()


async def _cleanup_stores(user_id: str) -> None:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    await client.execute_write(
        "MATCH (u:User {id: $user_id})-[*0..2]-(n) DETACH DELETE n",
        {"user_id": user_id},
    )
    from agentic.memory.pg_vector.client import get_pool

    pool = await get_pool()
    if pool is not None:
        for table in (
            "memory_embeddings", "experience_embeddings", "thought_embeddings",
            "trigger_embeddings", "behavior_embeddings",
        ):
            try:
                async with pool.acquire() as conn:
                    await conn.execute(f"DELETE FROM {table} WHERE user_id = $1::uuid", user_id)
            except Exception:
                pass


async def main() -> None:
    user_id = str(uuid.uuid4())
    session1_id = str(uuid.uuid4())
    session2_id = str(uuid.uuid4())

    print(f"user_id={user_id}")
    _ensure_user(user_id)
    _insert_session(user_id, session1_id, SESSION_1_TURNS)

    from agentic.memory.neo4j_client import init_client
    await init_client()

    from agentic.agent.session.finalizer_factory import build_session_finalizer

    finalizer = build_session_finalizer()

    print("\n--- Session 1: seeding catastrophic thought ---")
    result1 = await finalizer.finalize(session_id=session1_id, user_id=user_id, language="id")
    print(f"  extracted={result1.extracted_count} processed={result1.processed_count} error={result1.error}")
    if result1.error:
        print("Aborting: session 1 finalize failed.")
        _cleanup(user_id)
        return

    from agentic.memory.neo4j_client import get_client
    client = get_client()

    before = await client.execute_read(
        "MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(t:Thought) RETURN t.id AS id, t.content AS content, t.distortion AS distortion",
        {"user_id": user_id},
    )
    print(f"  Thought nodes after session 1: {json.dumps(before, ensure_ascii=False, indent=2, default=str)}")

    _insert_session(user_id, session2_id, SESSION_2_TURNS)
    print("\n--- Session 2: revising the belief ---")
    result2 = await finalizer.finalize(session_id=session2_id, user_id=user_id, language="id")
    print(f"  extracted={result2.extracted_count} processed={result2.processed_count} error={result2.error}")

    print("\n--- Checking Neo4j for lifecycle relations ---")
    supersedes = await client.execute_read(
        """
        MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(new:Thought)-[r:SUPERSEDES]->(old:Thought)
        RETURN old.id AS old_id, old.content AS old_content, old.active AS old_active,
               new.id AS new_id, new.content AS new_content, r.reason AS reason
        """,
        {"user_id": user_id},
    )
    reappraisals = await client.execute_read(
        """
        MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(old:Experience)-[r:REAPPRAISED_AS]->(new:Experience)
        RETURN old.id AS old_id, old.description AS old_description, old.active AS old_active,
               new.id AS new_id, new.description AS new_description
        """,
        {"user_id": user_id},
    )
    all_thoughts_after = await client.execute_read(
        "MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(t:Thought) RETURN t.id AS id, t.content AS content, t.active AS active",
        {"user_id": user_id},
    )
    all_experiences_after = await client.execute_read(
        "MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience) RETURN e.id AS id, e.description AS description, e.active AS active",
        {"user_id": user_id},
    )

    print(f"\nSUPERSEDES relations found: {len(supersedes)}")
    print(json.dumps(supersedes, ensure_ascii=False, indent=2, default=str))
    print(f"\nREAPPRAISED_AS relations found: {len(reappraisals)}")
    print(json.dumps(reappraisals, ensure_ascii=False, indent=2, default=str))
    print(f"\nAll Thought nodes after session 2: {json.dumps(all_thoughts_after, ensure_ascii=False, indent=2, default=str)}")
    print(f"\nAll Experience nodes after session 2: {json.dumps(all_experiences_after, ensure_ascii=False, indent=2, default=str)}")

    with open(ROOT / "evaluation_pipeline" / "results" / "reappraisal_probe.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "user_id": user_id,
                "session1_result": {"extracted": result1.extracted_count, "processed": result1.processed_count, "error": result1.error},
                "session2_result": {"extracted": result2.extracted_count, "processed": result2.processed_count, "error": result2.error},
                "thoughts_after_session1": before,
                "supersedes_relations": supersedes,
                "reappraised_as_relations": reappraisals,
                "all_thoughts_after": all_thoughts_after,
                "all_experiences_after": all_experiences_after,
            },
            f, ensure_ascii=False, indent=2, default=str,
        )

    print("\nCleaning up test data...")
    await _cleanup_stores(user_id)
    _cleanup(user_id)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

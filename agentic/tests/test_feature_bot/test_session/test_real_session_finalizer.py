"""test real sess fin"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from agentic.agent.session.finalizer_factory import build_session_finalizer
from agentic.memory.neo4j_client import close_client, get_client, init_client
from agentic.memory.pg_vector.client import close_pool, get_pool


# set ses ID
SESSION_ID= "7915b875-6970-4d1c-b215-78afd070b652"
ROOT = Path(__file__).resolve().parents[4]
EMBEDDING_TABLES = {
    "Memory": "memory_embeddings",
    "Experience": "experience_embeddings",
    "Thought": "thought_embeddings",
    "Trigger": "trigger_embeddings",
}


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


def _json_default(value: Any) -> str:
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return str(value)


async def _load_session_info(session_id: str) -> dict[str, Any]:
    pool = await get_pool()
    if pool is None:
        pytest.skip("Postgres unavailable. Check PG_* env values.")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                cs.id::text AS session_id,
                cs.user_id::text AS user_id,
                cs.channel,
                cs.status,
                cs.turn_count,
                cs.started_at,
                cs.ended_at,
                count(m.id)::int AS message_count,
                min(m.turn_index)::int AS first_turn_index,
                max(m.turn_index)::int AS last_turn_index
            FROM chat_sessions cs
            LEFT JOIN messages m ON m.session_id = cs.id
            WHERE cs.id = $1::uuid
            GROUP BY cs.id
            """,
            session_id,
        )

    if row is None:
        pytest.fail(f"session not found in Postgres: {session_id}")
    return dict(row)


async def _neo4j_session_nodes(user_id: str, session_id: str) -> dict[str, Any]:
    params = {"user_id": user_id, "session_id": session_id}
    rows: list[dict[str, Any]] = []
    for query in (
        """
        MATCH (u:User {id: $user_id})-[r]->(n)
        WHERE r.source_session = $session_id
        RETURN labels(n)[0] AS label, n.id AS id
        """,
        """
        MATCH (:Session {id: $session_id})-[r]->(n)
        RETURN labels(n)[0] AS label, n.id AS id
        """,
        """
        MATCH (n)
        WHERE n.source_session_id = $session_id
        RETURN labels(n)[0] AS label, n.id AS id
        """,
    ):
        rows.extend(await get_client().execute_read(query, params))

    by_label: dict[str, Any] = {}
    for row in rows:
        label = row.get("label") or "Unknown"
        item_id = row.get("id")
        if not item_id:
            continue
        current = by_label.setdefault(label, {"ids": set()})
        current["ids"].add(str(item_id))

    for label, data in by_label.items():
        ids = sorted(data["ids"])
        by_label[label] = {"count": len(ids), "ids": ids}
    return by_label


async def _neo4j_session_relations(session_id: str) -> dict[str, int]:
    rows = await get_client().execute_read(
        """
        MATCH ()-[r]->()
        WHERE r.source_session = $session_id
        RETURN type(r) AS type, count(r) AS count
        ORDER BY type
        """,
        {"session_id": session_id},
    )
    return {str(row["type"]): int(row["count"]) for row in rows}


async def _pgvector_counts(
    *,
    user_id: str,
    neo4j_nodes: dict[str, Any],
) -> dict[str, Any]:
    pool = await get_pool()
    if pool is None:
        return {"available": False, "tables": {}}

    result: dict[str, Any] = {"available": True, "tables": {}}
    async with pool.acquire() as conn:
        for label, table in EMBEDDING_TABLES.items():
            ids = neo4j_nodes.get(label, {}).get("ids", [])
            session_vectors = 0
            if ids:
                session_vectors = int(
                    await conn.fetchval(
                        f"""
                        SELECT count(*)::int
                        FROM {table}
                        WHERE user_id = $1::uuid
                          AND active = TRUE
                          AND neo4j_node_id = ANY($2::varchar[])
                        """,
                        user_id,
                        ids,
                    )
                    or 0
                )

            user_active_vectors = int(
                await conn.fetchval(
                    f"""
                    SELECT count(*)::int
                    FROM {table}
                    WHERE user_id = $1::uuid
                      AND active = TRUE
                    """,
                    user_id,
                )
                or 0
            )
            result["tables"][label] = {
                "session_node_ids": len(ids),
                "session_vectors": session_vectors,
                "user_active_vectors": user_active_vectors,
            }
    return result


async def _snapshot(user_id: str, session_id: str) -> dict[str, Any]:
    nodes = await _neo4j_session_nodes(user_id, session_id)
    return {
        "kg_nodes": {
            label: data["count"]
            for label, data in nodes.items()
        },
        "kg_relations": await _neo4j_session_relations(session_id),
        "pgvector": await _pgvector_counts(user_id=user_id, neo4j_nodes=nodes),
    }


@pytest.mark.asyncio
async def test_real_session_finalizer_writes_kg_and_pgvector() -> None:
    if os.getenv("AXIS_RUN_REAL_FINALIZER_TEST") != "1":
        pytest.skip("Set AXIS_RUN_REAL_FINALIZER_TEST=1 to run this real DB/LLM test.")

    _load_env_file(ROOT / ".env")
    _load_env_file(ROOT / "agentic" / ".env")

    await init_client()
    try:
        session = await _load_session_info(SESSION_ID)
        user_id = session["user_id"]
        before = await _snapshot(user_id, SESSION_ID)

        started = time.perf_counter()
        result = await build_session_finalizer().finalize(
            session_id=SESSION_ID,
            user_id=user_id,
            language="id",
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        after = await _snapshot(user_id, SESSION_ID)

        report = {
            "session": session,
            "finalizer": {
                "session_id": result.session_id,
                "processed_count": result.processed_count,
                "extracted_count": result.extracted_count,
                "through_turn_index": result.through_turn_index,
                "summary_chars": len(result.summary or ""),
                "error": result.error,
            },
            "duration_ms": duration_ms,
            "before": before,
            "after": after,
        }
        print("\nREAL_SESSION_FINALIZER_REPORT")
        print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))

        assert result.error is None
        assert result.processed_count > 0
        assert result.summary
        assert sum(after["kg_nodes"].values()) >= sum(before["kg_nodes"].values())
        assert after["pgvector"]["available"] is True
    finally:
        await close_client()
        await close_pool()

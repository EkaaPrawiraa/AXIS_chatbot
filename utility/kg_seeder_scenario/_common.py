"""
utility/kg_seeder_scenario/_common.py

Shared infrastructure for all KG seeder scenarios.

Provides:
  - Postgres helpers (connection, user/session upsert, pgvector upsert, purge)
  - Neo4j tag / purge helpers
  - Assessment node writer  (mirrors what Go's WriteAssessment does)
  - Thought supersession writer (CBT reframe arc)
  - Deterministic session-ID generator
  - Shared argparse builder

Import pattern in each seed.py:
    from utility.kg_seeder_scenario._common import (
        SeedConfig, _now, _iso, _is_uuid,
        _session_ids_for_namespace,
        _tag_node, _purge_namespace,
        _upsert_pg_user_and_sessions, _upsert_pg_embedding,
        _write_assessment_node, _write_supersession,
        _build_arg_parser,
    )
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5



@dataclass(frozen=True)
class SeedConfig:
    user_id: str
    namespace: str
    password_hash: str
    preferred_language: str = "id"



def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False


def _session_ids_for_namespace(namespace: str, count: int = 3) -> dict[str, str]:
    return {
        f"s{i+1}": str(uuid5(NAMESPACE_URL, f"{namespace}:session:{i+1:02d}"))
        for i in range(count)
    }



def _pg_dsn() -> str:
    return os.getenv(
        "PG_DSN",
        "postgresql://{user}:{password}@{host}:{port}/{database}".format(
            user=os.getenv("PG_USER", "companion"),
            password=os.getenv("PG_PASSWORD", "companion"),
            host=os.getenv("PG_HOST", "localhost"),
            port=os.getenv("PG_PORT", "5432"),
            database=os.getenv("PG_DATABASE", "companion"),
        ),
    )


async def _pg_connect():
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("Install asyncpg: pip install asyncpg") from exc
    return await asyncpg.connect(_pg_dsn())


async def _pg_available() -> bool:
    try:
        conn = await _pg_connect()
        try:
            await conn.execute("SELECT 1")
            return True
        finally:
            await conn.close()
    except Exception as exc:
        print(f"  [pg] unavailable — skipping pgvector mirror: {exc}")
        return False


async def _upsert_pg_user_and_sessions(
    cfg: SeedConfig,
    scenario_name: str,
    sessions: list[dict[str, Any]],
) -> None:
    """Upsert user + chat_sessions rows in Postgres."""
    if not await _pg_available():
        return
    conn = await _pg_connect()
    try:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO users (
                    id, email, display_name, password_hash,
                    preferred_language, onboarding_complete, account_status
                )
                VALUES ($1::uuid, $2, $3, $4, $5, true, 'active')
                ON CONFLICT (id) DO UPDATE SET
                    display_name      = EXCLUDED.display_name,
                    preferred_language = EXCLUDED.preferred_language,
                    updated_at        = now(),
                    deleted_at        = NULL
                """,
                cfg.user_id,
                f"{scenario_name}+{cfg.namespace}@seed.local",
                scenario_name,
                cfg.password_hash,
                cfg.preferred_language[:2],
            )
            for s in sessions:
                await conn.execute(
                    """
                    INSERT INTO chat_sessions (
                        id, user_id, neo4j_session_id, channel, status,
                        started_at, ended_at, turn_count, safety_escalated, kg_processed
                    )
                    VALUES (
                        $1::uuid, $2::uuid, $3, 'voice', 'ended',
                        $4::timestamptz, $5::timestamptz,
                        0, false, true
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        neo4j_session_id = EXCLUDED.neo4j_session_id,
                        status           = EXCLUDED.status,
                        started_at       = EXCLUDED.started_at,
                        ended_at         = EXCLUDED.ended_at,
                        kg_processed     = EXCLUDED.kg_processed
                    """,
                    s["id"], cfg.user_id, s["id"],
                    s["started_at"], s["ended_at"],
                )
    finally:
        await conn.close()


def _vector_literal(embedding: list[float]) -> str:
    if len(embedding) != 1536:
        raise ValueError(f"Expected 1536-dim embedding, got {len(embedding)}")
    return "[" + ",".join(str(float(x)) for x in embedding) + "]"


async def _upsert_pg_embedding(
    *,
    table: str,
    user_id: str,
    neo4j_node_id: str,
    content: str,
    embedding: list[float],
    importance: float = 0.5,
) -> None:
    _VALID_TABLES = {
        "experience_embeddings", "memory_embeddings",
        "thought_embeddings", "trigger_embeddings",
    }
    if table not in _VALID_TABLES:
        raise ValueError(f"Unsupported embedding table: {table}")
    if not await _pg_available():
        return
    conn = await _pg_connect()
    try:
        await conn.execute(
            f"""
            INSERT INTO {table} (user_id, neo4j_node_id, content, embedding, importance, active)
            VALUES ($1::uuid, $2, $3, $4::vector, $5, true)
            ON CONFLICT (neo4j_node_id) DO UPDATE SET
                content       = EXCLUDED.content,
                embedding     = EXCLUDED.embedding,
                importance    = EXCLUDED.importance,
                active        = true,
                last_accessed = now()
            """,
            user_id,
            neo4j_node_id,
            content,
            _vector_literal(embedding),
            float(importance),
        )
    finally:
        await conn.close()



async def _tag_node(*, node_id: str, namespace: str) -> None:
    from agentic.memory.neo4j_client import get_client
    await get_client().execute_write(
        "MATCH (n {id: $id}) SET n.seed_namespace = $ns",
        {"id": node_id, "ns": namespace},
    )


async def _seeded_node_ids_by_label(namespace: str) -> dict[str, list[str]]:
    from agentic.memory.neo4j_client import get_client
    rows = await get_client().execute_read(
        "MATCH (n) WHERE n.seed_namespace = $ns RETURN labels(n) AS labels, n.id AS id",
        {"ns": namespace},
    )
    out: dict[str, list[str]] = {
        "Experience": [], "Memory": [], "Thought": [], "Trigger": [],
    }
    for row in rows:
        labels = set(row.get("labels", []))
        node_id = row.get("id")
        if not node_id:
            continue
        for label in out:
            if label in labels:
                out[label].append(node_id)
    return out


async def _purge_pg_for_namespace(
    namespace: str,
    session_ids: list[str],
    user_id: str | None = None,
) -> None:
    if not await _pg_available():
        return
    ids = await _seeded_node_ids_by_label(namespace)
    table_by_label = {
        "Experience": "experience_embeddings",
        "Memory":     "memory_embeddings",
        "Thought":    "thought_embeddings",
        "Trigger":    "trigger_embeddings",
    }
    conn = await _pg_connect()
    try:
        async with conn.transaction():
            for label, table in table_by_label.items():
                if ids[label]:
                    await conn.execute(
                        f"DELETE FROM {table} WHERE neo4j_node_id = ANY($1::varchar[])",
                        ids[label],
                    )
            if session_ids:
                await conn.execute(
                    "DELETE FROM chat_sessions WHERE id = ANY($1::uuid[])",
                    session_ids,
                )
            if user_id:
                await conn.execute(
                    "DELETE FROM users WHERE id = $1::uuid",
                    user_id,
                )
    finally:
        await conn.close()


async def _purge_namespace(
    namespace: str,
    session_ids: list[str],
    user_id: str | None = None,
) -> None:
    from agentic.memory.neo4j_client import get_client
    await _purge_pg_for_namespace(namespace, session_ids, user_id)
    await get_client().execute_write(
        "MATCH (n) WHERE n.seed_namespace = $ns DETACH DELETE n",
        {"ns": namespace},
    )
    print(f"Purged namespace: {namespace}")


# Assessment node writer
# Mirrors Go's WriteAssessment + MarkPHQ9Administered.
# Python never creates Assessment nodes during normal operation because
# save_phq9_result only writes to Postgres. This helper lets the seeder
# create the full Neo4j representation that Go would produce.


async def _write_assessment_node(
    *,
    user_id: str,
    session_id: str,
    instrument: str,
    score: int,
    severity_label: str,
    item_responses: dict[str, int],
    delta_from_previous: int | None,
    q9_score: int,
    administered_at: str,
    namespace: str,
) -> str:
    """
    Write an Assessment node to Neo4j, replicating what Go's WriteAssessment
    produces. Creates both:
      (User)-[:COMPLETED_ASSESSMENT]->(Assessment)
      (Session)-[:PRODUCED_ASSESSMENT]->(Assessment)
    and sets Session.phq9_administered = true.

    Returns the assessment node id.
    """
    from agentic.memory.neo4j_client import get_client
    import json

    assessment_id = str(uuid4())
    item_json = json.dumps(item_responses)

    await get_client().execute_write(
        """
        MATCH (u:User    {id: $user_id})
        MATCH (s:Session {id: $session_id})
        CREATE (a:Assessment {
            id:                  $a_id,
            instrument:          $instrument,
            score:               $score,
            severity_label:      $severity_label,
            delta_from_previous: $delta,
            administered_at:     datetime($administered_at),
            q9_score:            $q9_score,
            item_responses:      $item_responses,
            sensitivity_level:   'normal',
            seed_namespace:      $ns
        })
        CREATE (u)-[:COMPLETED_ASSESSMENT {
            t_valid:        datetime($administered_at),
            t_invalid:      null,
            source_session: $session_id,
            confidence:     1.0
        }]->(a)
        CREATE (s)-[:PRODUCED_ASSESSMENT {
            t_valid:        datetime($administered_at),
            t_invalid:      null,
            source_session: $session_id,
            confidence:     1.0
        }]->(a)
        SET s.phq9_administered = true
        """,
        {
            "user_id":         user_id,
            "session_id":      session_id,
            "a_id":            assessment_id,
            "instrument":      instrument,
            "score":           score,
            "severity_label":  severity_label,
            "delta":           delta_from_previous,
            "q9_score":        q9_score,
            "item_responses":  item_json,
            "administered_at": administered_at,
            "ns":              namespace,
        },
    )
    return assessment_id


# Thought supersession helper
# Creates the CBT reframe arc:
#   (new:Thought)-[:SUPERSEDES {reason, at}]->(old:Thought)
# Sets old_thought.active = false, new_thought.challenged = true.


async def _write_supersession(
    *,
    old_thought_id: str,
    new_thought_id: str,
    reason: str,
    session_id: str,
    at: str,
) -> None:
    """
    Link two already-created Thought nodes with a SUPERSEDES edge.
    Sets old node active=false and new node challenged=true.

    Call AFTER both thoughts have been written with write_thought().
    The caller is responsible for writing the embedding for new_thought.
    """
    from agentic.memory.neo4j_client import get_client

    await get_client().execute_write(
        """
        MATCH (old:Thought {id: $old_id})
        MATCH (new:Thought {id: $new_id})
        CREATE (new)-[:SUPERSEDES {
            reason:         $reason,
            at:             datetime($at),
            source_session: $session_id,
            t_valid:        datetime($at),
            t_invalid:      null
        }]->(old)
        SET old.active      = false,
            old.superseded  = true,
            new.challenged  = true,
            new.active      = true
        """,
        {
            "old_id":     old_thought_id,
            "new_id":     new_thought_id,
            "reason":     reason,
            "at":         at,
            "session_id": session_id,
        },
    )



def _build_arg_parser(description: str, default_user_id: str, default_namespace: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--run",   action="store_true", help="seed the scenario")
    ap.add_argument("--purge", action="store_true", help="delete nodes for this namespace")
    ap.add_argument("--user-id",   default=default_user_id,   help="Neo4j User.id (UUID)")
    ap.add_argument("--namespace", default=default_namespace,  help="seed namespace tag")
    ap.add_argument("--lang",      default="id",               help="User.preferred_language")
    ap.add_argument(
        "--allow-non-uuid-user-id",
        action="store_true",
        help="Skip UUID check (Neo4j-only; pgvector upserts will fail)",
    )
    return ap


__all__ = [
    "SeedConfig",
    "_now", "_iso", "_is_uuid",
    "_session_ids_for_namespace",
    "_pg_available",
    "_upsert_pg_user_and_sessions",
    "_upsert_pg_embedding",
    "_tag_node",
    "_purge_namespace",
    "_write_assessment_node",
    "_write_supersession",
    "_build_arg_parser",
]

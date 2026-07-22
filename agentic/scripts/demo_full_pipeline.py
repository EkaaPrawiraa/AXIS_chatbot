"""skip prod"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# set env
ROOT = Path(__file__).resolve().parents[2]

def _load_env(path: Path) -> None:
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

_load_env(ROOT / ".env")
_load_env(ROOT / "agentic" / ".env")

USER_ID = "6aca3b8b-ddcf-4428-824e-997f921d28d3"

# skip queries
TEST_QUERIES = [
    "aku lagi sedih, temen-temenku ngebully lagi",
    "lu inget apa aja tentang gua?",
    "aku takut data aku ga aman",
]


def _json_default(v: Any) -> str:
    iso = getattr(v, "isoformat", None)
    if callable(iso):
        return iso()
    return str(v)


async def fetch_kg_signals_raw(user_id: str) -> dict[str, Any]:
    """ambil data"""
    from agentic.memory.neo4j_client import get_client

    result: dict[str, Any] = {}

    # buat nyimpan last 2 sesi
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:HAD_SESSION]->(s:Session)
            WHERE s.ended_at IS NOT NULL AND s.summary IS NOT NULL
            RETURN s.summary AS summary, s.started_at AS started_at
            ORDER BY s.started_at DESC LIMIT 2
            """,
            {"user_id": user_id},
        )
        result["recency_summaries"] = [dict(r) for r in records]
    except Exception as e:
        result["recency_summaries"] = f"ERROR: {e}"

    # skip mem nodes
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
            WHERE m.active = true AND m.sensitivity_level = 'normal' AND m.importance > 0.5
            RETURN m.summary AS summary, m.importance AS importance, m.id AS id
            ORDER BY m.importance DESC LIMIT 5
            """,
            {"user_id": user_id},
        )
        result["salient_memories"] = [dict(r) for r in records]
    except Exception as e:
        result["salient_memories"] = f"ERROR: {e}"

    # buat nyimpan config
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[r:HAS_SUBJECT]->(p:Subject)
            WHERE r.t_invalid IS NULL
            OPTIONAL MATCH (p)<-[ip:INVOLVES_SUBJECT]-(e:Experience)
              WHERE e.active = true AND ip.t_invalid IS NULL
            WITH p, r, collect(DISTINCT e.description) AS all_experiences
            WITH p, r, [d IN all_experiences WHERE d IS NOT NULL][..3] AS experiences
            RETURN p.name AS name, p.role AS role, p.sentiment AS sentiment,
                   r.quality AS relationship_quality,
                   coalesce(p.mention_count, 0) AS mention_count,
                   experiences
            ORDER BY coalesce(p.mention_count, 0) DESC, abs(coalesce(p.sentiment, 0.0)) DESC
            LIMIT 5
            """,
            {"user_id": user_id},
        )
        result["important_subjects"] = [dict(r) for r in records]
    except Exception as e:
        result["important_subjects"] = f"ERROR: {e}"

    # emotions 6 lama 7 hari
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:FELT]->(em:Emotion)
            WHERE em.active = true AND em.timestamp > datetime() - duration('P7D')
            RETURN em.label AS label, em.intensity AS intensity, em.valence AS valence
            ORDER BY em.timestamp DESC LIMIT 5
            """,
            {"user_id": user_id},
        )
        result["active_emotions"] = [dict(r) for r in records]
    except Exception as e:
        result["active_emotions"] = f"ERROR: {e}"

    # skip
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:HAS_THOUGHT]->(th:Thought)
            WHERE th.distortion IS NOT NULL AND th.challenged = false
            RETURN th.content AS content, th.distortion AS distortion,
                   th.believability AS believability
            ORDER BY th.timestamp DESC LIMIT 3
            """,
            {"user_id": user_id},
        )
        result["active_distortions"] = [dict(r) for r in records]
    except Exception as e:
        result["active_distortions"] = f"ERROR: {e}"

    # skip
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:HAS_TRIGGER]->(t:Trigger)
            WHERE t.active = true
            RETURN t.category AS category, t.description AS description,
                   t.frequency AS frequency
            ORDER BY t.frequency DESC LIMIT 3
            """,
            {"user_id": user_id},
        )
        result["recurring_triggers"] = [dict(r) for r in records]
    except Exception as e:
        result["recurring_triggers"] = f"ERROR: {e}"

    # skip
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[r:HAS_RECURRING_THEME]->(top:Topic)
            WHERE r.t_invalid IS NULL
            RETURN top.name AS topic, top.category AS category,
                   top.avg_sentiment AS avg_sentiment,
                   r.times_reinforced AS times_reinforced
            ORDER BY r.times_reinforced DESC, r.last_reinforced DESC
            LIMIT 5
            """,
            {"user_id": user_id},
        )
        result["recurring_themes"] = [dict(r) for r in records]
    except Exception as e:
        result["recurring_themes"] = f"ERROR: {e}"

    # bonus_exp
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:EXPERIENCED]->(e:Experience)
            WHERE e.active = true
            RETURN e.description AS description, e.valence AS valence,
                   e.significance AS significance, e.id AS id
            ORDER BY e.significance DESC LIMIT 10
            """,
            {"user_id": user_id},
        )
        result["all_experiences"] = [dict(r) for r in records]
    except Exception as e:
        result["all_experiences"] = f"ERROR: {e}"

    # skip beh
    try:
        records = await get_client().execute_read(
            """
            MATCH (u:User {id: $user_id})-[:EXHIBITED]->(b:Behavior)
            WHERE b.active = true
            RETURN b.description AS description, b.category AS category,
                   b.adaptive AS adaptive
            ORDER BY b.timestamp DESC LIMIT 5
            """,
            {"user_id": user_id},
        )
        result["all_behaviors"] = [dict(r) for r in records]
    except Exception as e:
        result["all_behaviors"] = f"ERROR: {e}"

    return result


async def fetch_pgvector_data(user_id: str) -> dict[str, Any]:
    """check tables"""
    from agentic.memory.pg_vector.client import get_pool

    pool = await get_pool()
    if not pool:
        return {"available": False}

    result: dict[str, Any] = {"available": True, "tables": {}}

    tables = {
        "Memory": "memory_embeddings",
        "Experience": "experience_embeddings",
        "Thought": "thought_embeddings",
        "Trigger": "trigger_embeddings",
    }

    async with pool.acquire() as conn:
        for label, table in tables.items():
            try:
                count = await conn.fetchval(
                    f"SELECT count(*)::int FROM {table} WHERE user_id = $1::uuid AND active = TRUE",
                    user_id,
                )
                # get it
                samples = await conn.fetch(
                    f"SELECT content, neo4j_node_id FROM {table} WHERE user_id = $1::uuid AND active = TRUE LIMIT 3",
                    user_id,
                )
                result["tables"][label] = {
                    "active_count": int(count or 0),
                    "samples": [{"content": s["content"][:200], "neo4j_id": s["neo4j_node_id"]} for s in samples],
                }
            except Exception as e:
                result["tables"][label] = {"error": str(e)}

    return result


async def run_build_context(user_id: str, query_text: str) -> tuple[str, Any]:
    """build_ctx()"""
    from agentic.memory.context_builder import build_context

    # skip error
    query_embedding = None
    try:
        from agentic.memory.pg_vector import embed_text
        query_embedding = await embed_text(query_text)
    except Exception as e:
        print(f"    ⚠️  Embedding failed: {e} — will skip semantic signals")

    ctx = await build_context(
        user_id=user_id,
        query_embedding=query_embedding,
        query_text=query_text,
    )

    return ctx.as_prompt_block(), ctx


async def main() -> None:
    from agentic.memory.neo4j_client import init_client, close_client
    from agentic.memory.pg_vector.client import close_pool

    await init_client()

    try:
        # ambil, kg, gak, error, skip, ngambil, config, init, state, db, conn, req, payload, skip, error, ngambil, gak, skip, ngambil, skip, ngambil, skip, ngambil, skip, ngambil, skip,
        print(f"\n{'='*80}")
        print(f"  PHASE 1: RAW KG SIGNALS FROM NEO4J (user={USER_ID[:12]}…)")
        print(f"{'='*80}\n")

        kg_raw = await fetch_kg_signals_raw(USER_ID)
        print(json.dumps(kg_raw, ensure_ascii=False, indent=2, default=_json_default))

        # `ubah ke array`
        print(f"\n{'='*80}")
        print(f"  PHASE 2: PGVECTOR EMBEDDING TABLES")
        print(f"{'='*80}\n")

        pgv = await fetch_pgvector_data(USER_ID)
        print(json.dumps(pgv, ensure_ascii=False, indent=2, default=_json_default))

        # build_ctx()
        print(f"\n{'='*80}")
        print(f"  PHASE 3: build_context() → as_prompt_block()")
        print(f"{'='*80}\n")

        context_blocks: dict[str, str] = {}
        for query in TEST_QUERIES:
            print(f"\n{'─'*80}")
            print(f"  Query: \"{query}\"")
            print(f"{'─'*80}")

            try:
                block, ctx = await run_build_context(USER_ID, query)
                context_blocks[query] = block
                print(f"\n{block}\n")

                # itungini
                stats = {
                    "recency_summaries": len(ctx.recency_summaries),
                    "semantic_memories": len(ctx.semantic_memories),
                    "salient_memories": len(ctx.salient_memories),
                    "semantic_experiences": len(ctx.semantic_experiences),
                    "focused_recall": bool(ctx.focused_recall),
                    "important_subjects": len(ctx.important_subjects),
                    "active_emotions": len(ctx.active_emotions),
                    "active_distortions": len(ctx.active_distortions),
                    "recurring_triggers": len(ctx.recurring_triggers),
                    "recurring_themes": len(ctx.recurring_themes),
                }
                print(f"  Signal stats: {json.dumps(stats)}")
            except Exception as e:
                print(f"  ❌ build_context failed: {e}")
                context_blocks[query] = ""
                import traceback
                traceback.print_exc()

        # asmprompt
        print(f"\n{'='*80}")
        print(f"  PHASE 4: ASSEMBLED SYSTEM PROMPT (same as response_generator_node)")
        print(f"{'='*80}\n")

        from agentic.prompts import load_prompt

        base_prompt = load_prompt("nodes/response_generator_v2")
        identity_prompt = load_prompt("system/axis_identity")

        for query in TEST_QUERIES:
            kg_context = context_blocks.get(query, "")
            if not kg_context:
                continue

            system_parts = [base_prompt, identity_prompt]
            if kg_context:
                system_parts.append(kg_context)
            system_parts.append(
                "LANGUAGE POLICY (mandatory): Mirror the user's language. "
                "If the user used Indonesian, reply in Indonesian. "
                "resolved_language=id; detected_user_language=id."
            )
            full_system = "\n\n".join(system_parts).strip()

            print(f"\n{'─'*80}")
            print(f"  Query: \"{query}\"")
            print(f"  System prompt length: {len(full_system)} chars")
            print(f"{'─'*80}")
            print(f"\n{full_system}\n")

    finally:
        await close_client()
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

"""Re-embed all pgvector rows with the current embedding provider.

This script reads every active row from memory_embeddings and
experience_embeddings, calls embed_text() (currently Gemini/local),
and overwrites the stored vector in-place.

Run from agentic/ directory:
    python scripts/reembed_pgvector.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agentic.memory.neo4j_client import init_client
from agentic.memory.pg_vector.client import get_pool
from agentic.memory.pg_vector import embed_text
from agentic.memory.pg_vector._common import vector_literal
from agentic.memory.pg_vector.embeddings import EMBED_MODEL, EMBED_PROVIDER, EMBED_DIM

TABLES = ["memory_embeddings", "experience_embeddings", "thought_embeddings", "trigger_embeddings"]
BATCH_SIZE = 10


async def reembed_table(table: str) -> dict:
    pool = await get_pool()
    if pool is None:
        print(f"  [skip] no pgvector pool")
        return {"table": table, "ok": 0, "fail": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT id, neo4j_node_id, content, user_id FROM {table} WHERE active = TRUE"
        )

    total = len(rows)
    ok = 0
    fail = 0
    print(f"  {table}: {total} rows to re-embed")

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        tasks = [embed_text(str(r["content"])) for r in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        async with pool.acquire() as conn:
            for r, emb in zip(batch, results):
                if isinstance(emb, Exception):
                    fail += 1
                    continue
                if not emb or len(emb) != EMBED_DIM:
                    fail += 1
                    continue
                vec = vector_literal(emb)
                await conn.execute(
                    f"UPDATE {table} SET embedding = $1::vector WHERE id = $2",
                    vec, r["id"],
                )
                ok += 1

        pct = min((i + BATCH_SIZE) / total * 100, 100)
        print(f"    [{table}] {i + len(batch)}/{total} ({pct:.0f}%) ok={ok} fail={fail}", end="\r")

    print(f"\n  {table}: done — ok={ok} fail={fail}")
    return {"table": table, "ok": ok, "fail": fail}


async def main():
    print(f"Re-embedding with provider={EMBED_PROVIDER} model={EMBED_MODEL} dim={EMBED_DIM}")
    await init_client()

    t0 = time.perf_counter()
    for table in TABLES:
        await reembed_table(table)

    elapsed = time.perf_counter() - t0
    print(f"\nDone in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

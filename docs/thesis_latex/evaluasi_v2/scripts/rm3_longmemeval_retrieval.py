"""Evaluate AXIS's production vector retrieval with LongMemEval evidence labels.

The public LongMemEval corpus provides session-level answer evidence. This
adapter writes each session summary through AXIS's Memory writer, retrieves
with the production pgvector search, then evaluates the ranked session IDs.
It deliberately does not claim a graph-vs-vector comparison: LongMemEval has
no AXIS node/relation annotations and the adapter does not synthesize them.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import psycopg2


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

SOURCE = ROOT / "docs/thesis_latex/evaluasi_v2/rm3_memori/external_data/longmemeval_s_cleaned.json"
OUTPUT = ROOT / "docs/thesis_latex/evaluasi_v2/rm3_memori/longmemeval_retrieval_results.json"
SAMPLE_PER_TYPE = 2
TOP_K = 5
SEED = 20260714
N_BOOTSTRAP = 10_000


def load_agentic_env() -> None:
    path = ROOT / "agentic/.env"
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def select_questions(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["question_type"])].append(row)
    rng = random.Random(SEED)
    selected: list[dict] = []
    for question_type in sorted(grouped):
        candidates = grouped[question_type]
        rng.shuffle(candidates)
        selected.extend(candidates[:SAMPLE_PER_TYPE])
    return selected


def session_summary(session: list[dict]) -> str:
    user_turns = [str(turn.get("content", "")).strip() for turn in session if turn.get("role") == "user"]
    text = " ".join(turn for turn in user_turns if turn)
    if not text:
        text = " ".join(str(turn.get("content", "")).strip() for turn in session)
    if not text:
        text = "[Sesi tanpa isi teks yang dapat diindeks]"
    return text[:1800]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Use AXIS's configured Gemini embedding model in provider-supported batches."""
    from google import genai
    from google.genai import types
    from agentic.memory.pg_vector.embeddings import EMBED_DIM, EMBED_MODEL, _fit_dimension

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    response = await asyncio.to_thread(
        client.models.embed_content,
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=EMBED_DIM),
    )
    embeddings = getattr(response, "embeddings", None) or []
    if len(embeddings) != len(texts):
        raise RuntimeError(f"Gemini returned {len(embeddings)} embeddings for {len(texts)} texts")
    return [_fit_dimension(list(item.values), source="gemini") for item in embeddings]


def postgres_connection():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=os.environ["PG_PORT"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        dbname=os.environ["PG_DATABASE"],
    )


def ensure_postgres_user(user_id: str) -> None:
    conn = postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status)
                VALUES (%s, %s, 'LongMemEval retrieval fixture', 'not-for-login', 'en', true, 'active')
                """
                "ON CONFLICT (id) DO NOTHING",
                (user_id, f"longmemeval-{user_id}@test.local"),
            )
        conn.commit()
    finally:
        conn.close()


async def create_kg_anchors(user_id: str, session_ids: list[str]) -> None:
    from agentic.memory.neo4j_client import get_client

    client = get_client()
    await client.execute_write(
        """
        MERGE (u:User {id: $user_id})
        SET u.display_name = 'LongMemEval retrieval fixture', u.active = true
        WITH u
        UNWIND $session_ids AS session_id
        MERGE (s:Session {id: session_id})
        SET s.started_at = datetime(), s.last_activity = datetime(), s.active = false
        MERGE (u)-[:HAD_SESSION {confidence: 1.0}]->(s)
        SET s.last_activity = datetime()
        """,
        {"user_id": user_id, "session_ids": session_ids},
    )


async def cleanup(user_id: str) -> None:
    from agentic.memory.neo4j_client import get_client
    from agentic.memory.pg_vector.client import get_pool

    client = get_client()
    await client.execute_write("MATCH (u:User {id: $user_id})-[*0..2]-(n) DETACH DELETE n", {"user_id": user_id})
    pool = await get_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM memory_embeddings WHERE user_id = $1::uuid", user_id)
    conn = postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def ranked_metrics(retrieved: list[str], relevant: set[str]) -> dict[str, float]:
    gains = [1 if session_id in relevant else 0 for session_id in retrieved]
    precision = sum(gains) / TOP_K
    recall = sum(gains) / len(relevant) if relevant else 0.0
    reciprocal_rank = next((1 / (index + 1) for index, gain in enumerate(gains) if gain), 0.0)
    dcg = sum(gain / __import__("math").log2(index + 2) for index, gain in enumerate(gains))
    ideal_gains = [1] * min(len(relevant), TOP_K)
    ideal_dcg = sum(gain / __import__("math").log2(index + 2) for index, gain in enumerate(ideal_gains))
    return {"p_at_5": precision, "recall_at_5": recall, "mrr": reciprocal_rank, "ndcg_at_5": dcg / ideal_dcg if ideal_dcg else 0.0}


def bootstrap_ci(results: list[dict], metric_names: tuple[str, ...]) -> dict[str, list[float]]:
    """Percentile bootstrap intervals for mean query-level retrieval metrics."""
    rng = random.Random(SEED)
    sample_size = len(results)
    intervals: dict[str, list[float]] = {}
    for name in metric_names:
        values = [float(row[name]) for row in results]
        estimates = []
        for _ in range(N_BOOTSTRAP):
            estimates.append(sum(values[rng.randrange(sample_size)] for _ in range(sample_size)) / sample_size)
        estimates.sort()
        intervals[name] = [
            estimates[int(0.025 * N_BOOTSTRAP)],
            estimates[int(0.975 * N_BOOTSTRAP)],
        ]
    return intervals


async def evaluate_question(question: dict) -> dict:
    from agentic.memory.knowledge_graph.kg_retriever.schemas import MemoryInput
    from agentic.memory.knowledge_graph.kg_writer import write_memory
    from agentic.memory.pg_vector.vector_retriever.search import search_memory

    user_id = str(uuid.uuid4())
    session_ids = [str(value) for value in question["haystack_session_ids"]]
    ensure_postgres_user(user_id)
    try:
        await create_kg_anchors(user_id, session_ids)
        node_to_session: dict[str, str] = {}
        summaries = [session_summary(session) for session in question["haystack_sessions"]]
        embeddings = await embed_batch(summaries + [str(question["question"])])
        for session_id, summary, embedding in zip(session_ids, summaries, embeddings[:-1]):
            if not summary:
                continue
            node_id = await write_memory(MemoryInput(
                summary=summary,
                importance=0.5,
                user_id=user_id,
                session_id=session_id,
                embedding=embedding,
            ))
            node_to_session[node_id] = session_id
        query_embedding = embeddings[-1]
        hits = await search_memory(user_id, query_embedding, top_k=TOP_K, min_similarity=None)
        retrieved = [node_to_session[hit.neo4j_node_id] for hit in hits if hit.neo4j_node_id in node_to_session]
        relevant = {str(value) for value in question["answer_session_ids"]}
        return {
            "question_id": question["question_id"],
            "question_type": question["question_type"],
            "n_sessions": len(session_ids),
            "n_relevant": len(relevant),
            "retrieved_session_ids": retrieved,
            "answer_session_ids": sorted(relevant),
            **ranked_metrics(retrieved, relevant),
        }
    finally:
        await cleanup(user_id)


async def main() -> None:
    load_agentic_env()
    from agentic.memory.neo4j_client import init_client, close_client

    rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    selected = select_questions(rows)
    await init_client()
    try:
        results = []
        for index, question in enumerate(selected, 1):
            print(f"[{index}/{len(selected)}] {question['question_id']} ({question['question_type']})", flush=True)
            results.append(await evaluate_question(question))
    finally:
        await close_client()
    metric_names = ("p_at_5", "recall_at_5", "mrr", "ndcg_at_5")
    summary = {name: sum(row[name] for row in results) / len(results) for name in metric_names}
    confidence_intervals = bootstrap_ci(results, metric_names)
    OUTPUT.write_text(json.dumps({
        "source": "LongMemEval_S cleaned, official repository",
        "source_file": str(SOURCE.relative_to(ROOT)),
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "sample_per_question_type": SAMPLE_PER_TYPE,
        "seed": SEED,
        "top_k": TOP_K,
        "n_bootstrap": N_BOOTSTRAP,
        "scope": "Production Memory writer plus pgvector ranking; not a graph-vs-vector ablation or extractor-quality evaluation.",
        "summary": summary,
        "bootstrap_ci95": confidence_intervals,
        "results": results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

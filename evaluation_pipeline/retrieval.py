"""Vector-only retrieval used by the baseline condition."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

import psycopg2
from openai import OpenAI

from config import CONFIG, EvaluationConfig, require_value


EMBEDDING_TABLES = (
    "memory_embeddings",
    "experience_embeddings",
    "thought_embeddings",
    "trigger_embeddings",
    "behavior_embeddings",
)


def embed_text(
    text: str,
    config: EvaluationConfig = CONFIG,
    *,
    task_type: str = "RETRIEVAL_QUERY",
) -> list[float]:
    provider = config.embedding_provider
    dimension = config.embedding_dimension

    if provider in {"gemini", "google"}:
        api_key = require_value(
            "GEMINI_API_KEY/GOOGLE_API_KEY for embeddings",
            config._embedding_api_key(),
        )
        model = config.embedding_model.removeprefix("models/")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model}:embedContent?key={api_key}"
        )
        payload = {
            "model": f"models/{model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
            "outputDimensionality": dimension,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(
            request, timeout=config.request_timeout_seconds
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
        embedding = body.get("embedding", {}).get("values", [])
    elif provider == "openai":
        client = OpenAI(api_key=config._embedding_api_key())
        response = client.embeddings.create(
            model=config.embedding_model,
            input=text,
            dimensions=dimension,
        )
        embedding = response.data[0].embedding
    else:
        client = OpenAI(
            api_key="not-needed",
            base_url=config.baseline_base_url,
        )
        response = client.embeddings.create(model=config.embedding_model, input=text)
        embedding = response.data[0].embedding

    if len(embedding) != dimension:
        raise RuntimeError(
            f"Embedding dimension mismatch: expected {dimension}, got {len(embedding)}. "
            "Do not truncate vectors in an evaluation run."
        )
    return [float(value) for value in embedding]


def _query_table(
    cursor: Any,
    *,
    table: str,
    user_id: str,
    embedding: list[float],
    candidate_k: int,
) -> list[dict[str, Any]]:
    if table not in EMBEDDING_TABLES:
        raise ValueError(f"Unsupported embedding table: {table}")
    vector_literal = "[" + ",".join(str(value) for value in embedding) + "]"
    cursor.execute(
        f"""
        SELECT id::text, neo4j_node_id, content, importance, created_at,
               1 - (embedding <=> %s::vector) AS similarity
        FROM {table}
        WHERE user_id = %s AND active = TRUE
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (vector_literal, user_id, vector_literal, candidate_k),
    )
    return [
        {
            "table": table,
            "id": row[0],
            "neo4j_node_id": row[1],
            "content": row[2],
            "importance": float(row[3]) if row[3] is not None else None,
            "created_at": row[4].isoformat() if row[4] else None,
            "similarity": float(row[5]),
        }
        for row in cursor.fetchall()
        if row[2]
    ]


def retrieve_memories(
    user_id: str,
    query: str,
    top_k: int | None = None,
    *,
    config: EvaluationConfig = CONFIG,
) -> list[dict[str, Any]]:
    config.validate_for(baseline=True)
    final_k = top_k or config.top_k
    embedding = embed_text(query, config)
    candidate_k = max(final_k, 1)

    all_results: list[dict[str, Any]] = []
    with psycopg2.connect(config.database_url) as connection:
        with connection.cursor() as cursor:
            for table in EMBEDDING_TABLES:
                try:
                    all_results.extend(
                        _query_table(
                            cursor,
                            table=table,
                            user_id=user_id,
                            embedding=embedding,
                            candidate_k=candidate_k,
                        )
                    )
                except psycopg2.errors.UndefinedTable:
                    connection.rollback()

    seen: set[str] = set()
    ranked: list[dict[str, Any]] = []
    for result in sorted(
        all_results, key=lambda item: item["similarity"], reverse=True
    ):
        normalized = " ".join(result["content"].lower().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        ranked.append(result)
    return ranked[:final_k]

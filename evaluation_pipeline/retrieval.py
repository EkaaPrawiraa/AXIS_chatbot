from typing import List, Dict, Any

import psycopg2
from openai import OpenAI

from config import OPENAI_API_KEY, DATABASE_URL, EMBEDDING_MODEL

_openai_client = OpenAI(api_key=OPENAI_API_KEY)


def _embed(text: str) -> List[float]:
    response = _openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def _query_table(
    cursor,
    table: str,
    content_col: str,
    user_id: str,
    embedding: List[float],
    top_k: int,
) -> List[Dict[str, Any]]:
    vector_literal = "[" + ",".join(str(v) for v in embedding) + "]"
    sql = f"""
        SELECT
            id::text,
            {content_col} AS content,
            1 - (embedding <=> '{vector_literal}'::vector) AS similarity
        FROM {table}
        WHERE user_id = %s
        ORDER BY embedding <=> '{vector_literal}'::vector
        LIMIT %s;
    """
    cursor.execute(sql, (user_id, top_k))
    rows = cursor.fetchall()
    return [
        {
            "table": table,
            "id": row[0],
            "content": row[1],
            "similarity": float(row[2]),
        }
        for row in rows
        if row[1]
    ]


def retrieve_memories(user_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    embedding = _embed(query)

    tables = [
        ("memory_embeddings", "summary"),
        ("experience_embeddings", "description"),
        ("thought_embeddings", "content"),
        ("trigger_embeddings", "description"),
    ]

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            all_results: List[Dict[str, Any]] = []
            for table, content_col in tables:
                try:
                    rows = _query_table(cur, table, content_col, user_id, embedding, top_k)
                    all_results.extend(rows)
                except Exception as e:
                    print(f"[retrieval] Skipping table {table}: {e}")
                    conn.rollback()
    finally:
        conn.close()

    seen_contents: set[str] = set()
    deduplicated: List[Dict[str, Any]] = []
    for result in sorted(all_results, key=lambda r: r["similarity"], reverse=True):
        content = (result["content"] or "").strip()
        if content and content not in seen_contents:
            seen_contents.add(content)
            deduplicated.append(result)

    return deduplicated[:top_k]

"""init state"""

from __future__ import annotations

from agentic.memory.pg_vector.client     import (
    PgvectorConfig,
    get_pool,
    close_pool,
    is_available,
)
from agentic.memory.pg_vector.embeddings import (
    EMBED_DIM,
    embed_text,
    embed_many,
)
from agentic.memory.pg_vector.vector_writer    import (
    upsert_memory,
    upsert_experience,
    upsert_thought,
    upsert_trigger,
    upsert_behavior,
)
from agentic.memory.pg_vector.vector_retriever import (
    SearchHit,
    search_memory,
    search_experience,
    search_thought,
    search_trigger,
    search_behavior,
)
from agentic.memory.pg_vector.vector_modifier  import (
    archive_node,
    purge_node,
    purge_user,
)

__all__ = [
    # buat nyimpan config
    "PgvectorConfig",
    "get_pool",
    "close_pool",
    "is_available",
    # emb.
    "EMBED_DIM",
    "embed_text",
    "embed_many",
    # write short
    "upsert_memory",
    "upsert_experience",
    "upsert_thought",
    "upsert_trigger",
    "upsert_behavior",
    # baca, skip
    "SearchHit",
    "search_memory",
    "search_experience",
    "search_thought",
    "search_trigger",
    "search_behavior",
    # archival
    "archive_node",
    "purge_node",
    "purge_user",
]

"""agentic/memory/pg_vector."""

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
    # config / lifecycle
    "PgvectorConfig",
    "get_pool",
    "close_pool",
    "is_available",
    # embeddings
    "EMBED_DIM",
    "embed_text",
    "embed_many",
    # writes
    "upsert_memory",
    "upsert_experience",
    "upsert_thought",
    "upsert_trigger",
    "upsert_behavior",
    # reads
    "SearchHit",
    "search_memory",
    "search_experience",
    "search_thought",
    "search_trigger",
    "search_behavior",
    # lifecycle / archival
    "archive_node",
    "purge_node",
    "purge_user",
]

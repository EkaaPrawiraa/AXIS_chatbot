-- Migration 019: Add behavior_embeddings pgvector mirror table.
-- Mirrors the Behavior KG node into pgvector for write-time dedup
-- and future semantic search over observable user actions.

CREATE TABLE IF NOT EXISTS behavior_embeddings (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID         NOT NULL,
    neo4j_node_id VARCHAR(64)  NOT NULL UNIQUE,
    content       TEXT         NOT NULL,
    embedding     vector(1536) NOT NULL,
    importance    FLOAT        NOT NULL DEFAULT 0.5,
    active        BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS behavior_embedding_hnsw
    ON behavior_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS behavior_user_active_idx
    ON behavior_embeddings (user_id, active);

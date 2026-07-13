-- Stores per-message LangGraph audit traces for backend/agentic evaluation.
-- One row represents one persisted user message entering the agentic graph.

CREATE TABLE IF NOT EXISTS agentic_graph_audits (
    id              BIGSERIAL PRIMARY KEY,
    message_id      UUID REFERENCES messages(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    message_content TEXT NOT NULL,
    graph           JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agentic_graph_audits_message_idx
    ON agentic_graph_audits (message_id);

CREATE INDEX IF NOT EXISTS agentic_graph_audits_user_created_idx
    ON agentic_graph_audits (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS agentic_graph_audits_session_created_idx
    ON agentic_graph_audits (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS agentic_graph_audits_graph_gin
    ON agentic_graph_audits USING GIN (graph);

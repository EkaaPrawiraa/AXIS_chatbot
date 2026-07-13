-- migrations/003_assessments.up.sql

CREATE TABLE assessments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id),
    neo4j_node_id   VARCHAR(64),           -- links to Assessment node in KG
    instrument      VARCHAR(20) NOT NULL,   -- PHQ-9 | GAD-7 | IPIP | EMA
    score           FLOAT,
    severity_label  VARCHAR(30),            -- minimal | mild | moderate | moderately_severe | severe
    item_responses  JSONB NOT NULL,         -- {q1: 2, q2: 1, ...}
    delta_from_prev FLOAT,                  -- positive = worsening
    administered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    administered_by VARCHAR(20) NOT NULL DEFAULT 'chatbot'  -- chatbot | therapist
);

CREATE INDEX assessments_user_time ON assessments (user_id, administered_at DESC);
CREATE INDEX assessments_instrument ON assessments (user_id, instrument, administered_at DESC);

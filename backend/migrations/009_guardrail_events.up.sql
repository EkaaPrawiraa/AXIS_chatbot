-- migrations/009_guardrail_events.up.sql
--
-- Cross-cutting telemetry for the guardrail stack. Every layer
-- (input, pre-generation crisis, post-generation, KG access) writes
-- here so the team can audit triggers, calibrate thresholds, and
-- evaluate efficacy after deployment.

CREATE TABLE IF NOT EXISTS guardrail_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    layer           VARCHAR(32) NOT NULL,           -- input | pre_gen | post_gen | kg_access
    event_type      VARCHAR(64) NOT NULL,           -- crisis_keyword | jailbreak | semantic_crisis | diagnostic_claim | clinical_instruction | sensitivity_block | rewrite_loop | safe_fallback
    decision        VARCHAR(32) NOT NULL,           -- allow | block | escalate | rewrite | fallback | redact | log_only
    severity        VARCHAR(16) NOT NULL DEFAULT 'info',  -- info | warn | critical
    trigger_detail  TEXT,                           -- regex/keyword/similarity score that fired
    latency_ms      INTEGER,
    metadata        JSONB,                          -- free-form (rewrite_attempt, similarity, etc.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS guardrail_events_user_time
    ON guardrail_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS guardrail_events_layer_time
    ON guardrail_events (layer, created_at DESC);
CREATE INDEX IF NOT EXISTS guardrail_events_severity_time
    ON guardrail_events (severity, created_at DESC)
    WHERE severity != 'info';

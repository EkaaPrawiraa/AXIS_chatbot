-- migrations/011_phq9_progress.up.sql
--
-- In-flight PHQ-9 administration state. One row per active session
-- per user. This is the authoritative server-side store for the
-- accumulated item scores while a PHQ-9 run is mid-flight, so the
-- Python service can recover the run after a restart, a stateless
-- LangServe invocation, or a request that forgets to round-trip the
-- `phq9_state` payload.
--
-- Lifecycle:
--   - INSERTed when the bot enters phase=offered or in_progress.
--   - UPSERTed after every PHQ-9 turn (score added, phase changed,
--     awaiting_clar set, etc.).
--   - DELETEd by the finalize node once the assessment row lands
--     in `assessments`, or when the user declines.
--
-- Final scores still go to `assessments`; this table is purely
-- ephemeral / pre-finalize.

CREATE TABLE phq9_progress (
    user_id        UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id     UUID         NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    phase          VARCHAR(20)  NOT NULL,
    active_item    SMALLINT,
    responses      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    back_count     SMALLINT     NOT NULL DEFAULT 0,
    tier           VARCHAR(20),
    language       VARCHAR(8),
    user_initiated BOOLEAN      NOT NULL DEFAULT FALSE,
    started_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, session_id)
);

CREATE INDEX phq9_progress_user_recent
    ON phq9_progress (user_id, updated_at DESC);

CREATE INDEX phq9_progress_stale
    ON phq9_progress (updated_at)
    WHERE phase IN ('offered', 'in_progress', 'awaiting_clar');

-- migrations/010_session_activity.up.sql
--
-- Tracks session activity heartbeats for the asynchronous KG writer.
-- A session becomes eligible for finalization when:
--   1. last_activity_at < now() - finalize_idle_minutes (default 30)
--   2. ai_was_last_speaker = true
--   3. finalized_at IS NULL

CREATE TABLE IF NOT EXISTS session_activity (
    session_id          UUID PRIMARY KEY,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_activity_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ai_was_last_speaker BOOLEAN NOT NULL DEFAULT FALSE,
    finalized_at        TIMESTAMPTZ,
    finalize_attempts   INTEGER NOT NULL DEFAULT 0,
    last_error          TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS session_activity_pending
    ON session_activity (last_activity_at, ai_was_last_speaker)
    WHERE finalized_at IS NULL;

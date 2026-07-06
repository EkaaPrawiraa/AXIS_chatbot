-- migrations/015_session_activity_checkpoints.up.sql

ALTER TABLE session_activity
    ADD COLUMN IF NOT EXISTS latest_turn_index INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_finalized_turn_index INTEGER NOT NULL DEFAULT -1,
    ADD COLUMN IF NOT EXISTS last_checkpoint_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS session_activity_checkpoint_ready
    ON session_activity (latest_turn_index, last_finalized_turn_index)
    WHERE finalized_at IS NULL AND ai_was_last_speaker = TRUE;

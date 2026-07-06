-- migrations/015_session_activity_checkpoints.down.sql

DROP INDEX IF EXISTS session_activity_checkpoint_ready;

ALTER TABLE session_activity
    DROP COLUMN IF EXISTS last_checkpoint_at,
    DROP COLUMN IF EXISTS last_finalized_turn_index,
    DROP COLUMN IF EXISTS latest_turn_index;

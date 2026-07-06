-- migrations/012_chat_ui_metadata.down.sql

DROP INDEX IF EXISTS sessions_user_updated;

ALTER TABLE chat_sessions
    DROP COLUMN IF EXISTS updated_at,
    DROP COLUMN IF EXISTS title;

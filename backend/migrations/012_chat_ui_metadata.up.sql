-- migrations/012_chat_ui_metadata.up.sql
--
-- Frontend-facing chat metadata. The clinical/audit source of truth
-- remains chat_sessions + messages; these columns support ChatGPT-like
-- conversation lists without introducing a separate conversation table.

ALTER TABLE chat_sessions
    ADD COLUMN IF NOT EXISTS title VARCHAR(200) NOT NULL DEFAULT 'New Conversation',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS sessions_user_updated
    ON chat_sessions (user_id, updated_at DESC)
    WHERE status != 'abandoned';

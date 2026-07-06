-- Persist frontend-facing per-message metadata such as PHQ-9 quick-reply state.

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS messages_metadata_gin
    ON messages USING GIN (metadata);

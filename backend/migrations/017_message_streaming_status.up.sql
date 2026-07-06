-- migrations/017_message_streaming_status.up.sql
-- Adds a status column to messages to support incremental streaming persistence.
-- Existing rows default to 'complete'; in-flight streamed responses use 'streaming'.

ALTER TABLE messages ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'complete';

CREATE INDEX messages_streaming ON messages (session_id, status)
    WHERE status = 'streaming';

-- migrations/017_message_streaming_status.down.sql
DROP INDEX IF EXISTS messages_streaming;
ALTER TABLE messages DROP COLUMN IF EXISTS status;

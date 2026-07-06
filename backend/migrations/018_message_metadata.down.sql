DROP INDEX IF EXISTS messages_metadata_gin;

ALTER TABLE messages
    DROP COLUMN IF EXISTS metadata;

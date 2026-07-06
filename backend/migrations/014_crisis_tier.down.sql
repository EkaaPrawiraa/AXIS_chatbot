-- migrations/014_crisis_tier.down.sql
ALTER TABLE messages
    DROP COLUMN IF EXISTS crisis_tier;

-- migrations/008_assessment_retries.up.sql
--
-- Tracks scheduled retries for PHQ-9 offers. The trigger node looks
-- up the row keyed by user_id and skips offering until next_attempt_at
-- has passed. Only one pending retry per user is stored at a time;
-- the latest schedule overwrites prior ones.

CREATE TABLE IF NOT EXISTS assessment_retries (
    user_id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    next_attempt_at  TIMESTAMPTZ NOT NULL,
    reason           VARCHAR(64) NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS assessment_retries_due
    ON assessment_retries (next_attempt_at);

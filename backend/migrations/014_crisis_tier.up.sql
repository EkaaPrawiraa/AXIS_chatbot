-- migrations/014_crisis_tier.up.sql
--
-- Persist the crisis triage tier alongside the safety flag so that
-- the frontend can render the correct guardrail UI (e.g. hotline card
-- for tier 1 explicit active intent) when loading historical messages.

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS crisis_tier VARCHAR(8);

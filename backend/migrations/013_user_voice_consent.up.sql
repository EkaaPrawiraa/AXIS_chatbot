ALTER TABLE users
    ADD COLUMN preferred_voice_id VARCHAR(120),
    ADD COLUMN preferred_tts_model VARCHAR(40) DEFAULT 'v2_5_turbo',
    ADD COLUMN safety_terms_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN safety_terms_version VARCHAR(40),
    ADD COLUMN safety_terms_accepted_at TIMESTAMPTZ;

CREATE INDEX users_safety_terms_idx ON users (safety_terms_accepted) WHERE deleted_at IS NULL;

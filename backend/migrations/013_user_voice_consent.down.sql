DROP INDEX IF EXISTS users_safety_terms_idx;

ALTER TABLE users
    DROP COLUMN IF EXISTS safety_terms_accepted_at,
    DROP COLUMN IF EXISTS safety_terms_version,
    DROP COLUMN IF EXISTS safety_terms_accepted,
    DROP COLUMN IF EXISTS preferred_tts_model,
    DROP COLUMN IF EXISTS preferred_voice_id;

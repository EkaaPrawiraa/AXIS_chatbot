DROP INDEX IF EXISTS users_google_id_idx;
ALTER TABLE users DROP COLUMN IF EXISTS google_id;
ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;

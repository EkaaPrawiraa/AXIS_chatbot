-- Google Sign-In support. Password-only accounts keep password_hash set;
-- Google-only accounts (no password ever chosen) leave it NULL rather than
-- storing an unusable placeholder hash. google_id is Google's stable "sub"
-- claim, unique per Google account so it can be looked up directly without
-- re-verifying an ID token against email each time.
ALTER TABLE users
    ALTER COLUMN password_hash DROP NOT NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS users_google_id_idx ON users (google_id) WHERE google_id IS NOT NULL;

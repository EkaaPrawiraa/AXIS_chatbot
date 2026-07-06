-- Gender is optional (nullable until the user picks one in Profile) and
-- feeds into the agentic system prompt's USER PROFILE CONTEXT so the
-- companion can refer to the user naturally and pick the right avatar.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS gender VARCHAR(20);

ALTER TABLE users
    ADD CONSTRAINT users_gender_check CHECK (gender IS NULL OR gender IN ('pria', 'wanita'));

-- Daily mood check-in: one score (1-5) per user per calendar day, so the
-- agentic context builder can surface today's mood and a short trend to the
-- response generator prompt.

CREATE TABLE IF NOT EXISTS user_moods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mood_date DATE NOT NULL,
    mood_score SMALLINT NOT NULL CHECK (mood_score BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, mood_date)
);

CREATE INDEX IF NOT EXISTS user_moods_user_date_idx
    ON user_moods (user_id, mood_date DESC);

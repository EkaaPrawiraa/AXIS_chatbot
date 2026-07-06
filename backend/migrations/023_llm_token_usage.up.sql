-- Per-user, per-day LLM token usage, aggregated by model. Written by the
-- agentic service after every real LLM call (see agentic/agent/session/
-- token_usage_repo.py) so an admin can query actual Gemini/OpenAI spend
-- per user without waiting on provider billing dashboards. One row per
-- (user, day, model) rather than one row per call, so table size stays
-- bounded by users x days x model-count instead of message volume.
CREATE TABLE IF NOT EXISTS llm_token_usage_daily (
    user_id UUID NOT NULL,
    usage_date DATE NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens BIGINT NOT NULL DEFAULT 0,
    completion_tokens BIGINT NOT NULL DEFAULT 0,
    call_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, usage_date, model)
);

CREATE INDEX IF NOT EXISTS llm_token_usage_daily_date_idx ON llm_token_usage_daily (usage_date);

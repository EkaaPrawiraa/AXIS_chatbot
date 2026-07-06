-- migrations/009_guardrail_events.down.sql

DROP INDEX IF EXISTS guardrail_events_severity_time;
DROP INDEX IF EXISTS guardrail_events_layer_time;
DROP INDEX IF EXISTS guardrail_events_user_time;
DROP TABLE IF EXISTS guardrail_events;

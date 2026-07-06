-- migrations/010_session_activity.down.sql

DROP INDEX IF EXISTS session_activity_pending;
DROP TABLE IF EXISTS session_activity;

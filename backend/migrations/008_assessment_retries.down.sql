-- migrations/008_assessment_retries.down.sql

DROP INDEX IF EXISTS assessment_retries_due;
DROP TABLE IF EXISTS assessment_retries;

# Backups

This folder stores local database backup files.

## Structure

Backup files can be placed directly in this folder. Docker Compose mounts it into the Postgres container at `/backups`.

## Use

Start Postgres with Docker Compose, then use Postgres tools such as `pg_dump` or `psql` against `localhost:5433`.

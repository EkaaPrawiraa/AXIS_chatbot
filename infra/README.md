# Infra

This folder contains local infrastructure configuration for databases and runtime dependencies.

## Structure

- `postgres`: Postgres initialization SQL and pgvector setup.
- `neo4j`: Cypher schema and migration files for the knowledge graph.
- `redis`: Redis support configuration, if needed.

## Run

Start infrastructure services from the repository root:

```bash
docker compose -f docker-compose.dev.yml up postgres neo4j redis
```

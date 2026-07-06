# Utility

This folder contains data utilities, including scenario seeders for the knowledge graph.

## Structure

- `kg_seeder_scenario`: scenario-based seed data for Neo4j and pgvector.
- `languange`: language-related utility data or experiments.

## Run Seeder

After the Docker services are ready, run a scenario from the repository root:

```bash
docker compose -f docker-compose.dev.yml run --rm agentic python utility/kg_seeder_scenario/scenario_1/seed.py
```

Replace `scenario_1` with another scenario folder when needed.

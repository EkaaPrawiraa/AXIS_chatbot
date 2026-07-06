# Scripts

This folder contains development, automation, and maintenance scripts for the repository.

## Structure

- `run_all.sh`: starts the full Docker development stack and runs a knowledge graph seeder.
- `run_*_tests.py`: local test runners for agentic feature areas.
- `*.md`: operational notes and database scripts.

## Run

Run scripts from the repository root so relative paths stay consistent:

```bash
./scripts/script-name
```

Start all Docker services and run the default seeder:

```bash
./scripts/run_all.sh
```

Run a specific seeder scenario:

```bash
SEED_SCENARIO=scenario_2 ./scripts/run_all.sh
```


kill $(lsof -t -i:[port number])

for port in 3000 3001 8000 8080 8081 8082 8083; do
  lsof -ti tcp:$port | xargs kill -9 2>/dev/null
done
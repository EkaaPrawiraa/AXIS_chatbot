#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.dev.yml}"
DEFAULT_SEED_SCENARIOS="scenario_1 scenario_2 scenario_3 scenario_4"
SEED_SCENARIOS="${SEED_SCENARIOS:-${DEFAULT_SEED_SCENARIOS}}"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found: ${COMPOSE_FILE}" >&2
  exit 1
fi

for scenario in ${SEED_SCENARIOS}; do
  seed_script="utility/kg_seeder_scenario/${scenario}/seed.py"
  if [[ ! -f "${seed_script}" ]]; then
    echo "Seeder not found: ${seed_script}" >&2
    echo "Set SEED_SCENARIOS to valid folders in utility/kg_seeder_scenario." >&2
    exit 1
  fi
done

echo "Starting full Docker development stack..."
docker compose -f "${COMPOSE_FILE}" up -d --build

echo "Running Postgres migrations..."
docker compose -f "${COMPOSE_FILE}" run --rm postgres-migrate

for scenario in ${SEED_SCENARIOS}; do
  seed_script="utility/kg_seeder_scenario/${scenario}/seed.py"
  echo "Running knowledge graph seeder: ${seed_script}"
  docker compose -f "${COMPOSE_FILE}" run --rm agentic python "${seed_script}"
done

echo "All services are running."
echo "Frontend: http://localhost:3000"
echo "Backend gateway: http://localhost:3001/api"
echo "Agentic: http://localhost:8000"

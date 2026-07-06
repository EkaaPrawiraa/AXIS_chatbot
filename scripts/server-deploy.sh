#!/usr/bin/env bash
# server-deploy.sh — Manual deploy script for the AXIS production server.
#
# Run this directly on the server when you want to deploy without triggering CI:
#   cd /opt/axis/CompanionshipChatBot
#   REPO_OWNER=your-github-username IMAGE_TAG=latest bash scripts/server-deploy.sh
#
# Or to roll back to the previous deploy:
#   IMAGE_TAG=rollback bash scripts/server-deploy.sh

set -euo pipefail

REPO_OWNER="${REPO_OWNER:?Set REPO_OWNER to your GitHub username (lowercase)}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DEPLOY_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_BASE="$DEPLOY_DIR/docker-compose.prod.yml"
COMPOSE_DEPLOY="$DEPLOY_DIR/docker-compose.deploy.yml"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

cd "$DEPLOY_DIR"

log "Deploying tag: $IMAGE_TAG"

# ── 1. Pull latest code ───────────────────────────────────────────────
log "[1/5] Pulling latest code..."
git fetch origin production
git reset --hard origin/production

# ── 2. Save rollback tag ──────────────────────────────────────────────
log "[2/5] Saving rollback snapshot..."
for svc in backend agentic frontend-v2; do
  src="ghcr.io/$REPO_OWNER/axis-$svc:current"
  dst="ghcr.io/$REPO_OWNER/axis-$svc:rollback"
  docker inspect "$src" &>/dev/null && docker tag "$src" "$dst" || true
done

# ── 3. Pull images ────────────────────────────────────────────────────
if [[ "$IMAGE_TAG" != "rollback" ]]; then
  log "[3/5] Pulling new images ($IMAGE_TAG)..."
  REPO_OWNER="$REPO_OWNER" IMAGE_TAG="$IMAGE_TAG" \
    docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEPLOY" pull \
      agentic backend-auth backend-chat backend-memory backend-gateway frontend

  # Tag as current for next rollback
  for svc in backend agentic frontend-v2; do
    docker tag "ghcr.io/$REPO_OWNER/axis-$svc:$IMAGE_TAG" \
               "ghcr.io/$REPO_OWNER/axis-$svc:current" || true
  done
else
  warn "[3/5] Rolling back to previous images..."
fi

# ── 4. Restart services ───────────────────────────────────────────────
log "[4/5] Starting services..."
REPO_OWNER="$REPO_OWNER" IMAGE_TAG="$IMAGE_TAG" \
  docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEPLOY" up -d \
    --no-build --remove-orphans

log "Waiting 30s for services to stabilise..."
sleep 30

# ── 5. Health check ───────────────────────────────────────────────────
log "[5/5] Checking health..."
HEALTHY=true

for svc in backend-gateway frontend; do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' \
    "$(docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_DEPLOY" ps -q "$svc" 2>/dev/null)" \
    2>/dev/null || echo "unknown")
  if [[ "$STATUS" != "healthy" ]]; then
    warn "$svc status: $STATUS"
    HEALTHY=false
  else
    log "$svc: healthy"
  fi
done

if [[ "$HEALTHY" != "true" ]]; then
  die "One or more services unhealthy. Check logs: docker compose logs <service>"
fi

# ── Cleanup ───────────────────────────────────────────────────────────
docker image prune -f --filter "until=72h" || true

log "==========================================="
log " Deploy complete: $IMAGE_TAG"
log "==========================================="
log " Gateway: http://$(hostname -I | awk '{print $1}'):3001"
log " Frontend v2: http://$(hostname -I | awk '{print $1}'):3000"
log " Logs: docker compose -f docker-compose.prod.yml -f docker-compose.deploy.yml logs -f"

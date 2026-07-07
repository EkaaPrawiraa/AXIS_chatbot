#!/usr/bin/env bash
# setup-server.sh — Bootstrap a fresh Ubuntu/Debian server for AXIS deployment.
# Run as root or with sudo.  Safe to re-run (all steps are idempotent).
# Usage:
#   chmod +x setup-server.sh
#   sudo ./setup-server.sh [--env /path/to/.env]

set -euo pipefail

ENV_FILE="${1:-}"
COMPOSE_VERSION="2.27.1"
MIGRATE_VERSION="4.17.1"
NEO4J_VERSION="5.26-community"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

[[ "$EUID" -eq 0 ]] || die "Run this script as root (sudo ./setup-server.sh)"
[[ "$(uname -s)" == "Linux" ]] || die "This script targets Linux (Ubuntu 22.04+ / Debian 12+)"

# ── 1. System packages ────────────────────────────────────────────────

log "Updating package index..."
apt-get update -qq

log "Installing base dependencies..."
apt-get install -y -qq \
  curl wget git unzip gnupg2 ca-certificates lsb-release \
  apt-transport-https software-properties-common \
  build-essential htop jq ufw

# ── 2. Docker Engine ──────────────────────────────────────────────────

if command -v docker &>/dev/null; then
  log "Docker already installed: $(docker --version)"
else
  log "Installing Docker Engine..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  log "Docker installed: $(docker --version)"
fi

# ── 3. Docker Compose (standalone) ───────────────────────────────────

COMPOSE_BIN="/usr/local/bin/docker-compose"
if [[ -f "$COMPOSE_BIN" ]] && "$COMPOSE_BIN" version 2>/dev/null | grep -q "$COMPOSE_VERSION"; then
  log "docker-compose $COMPOSE_VERSION already present"
else
  log "Installing docker-compose v${COMPOSE_VERSION}..."
  ARCH=$(uname -m); [[ "$ARCH" == "x86_64" ]] && ARCH="x86_64" || ARCH="aarch64"
  curl -fsSL \
    "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-${ARCH}" \
    -o "$COMPOSE_BIN"
  chmod +x "$COMPOSE_BIN"
  log "docker-compose installed: $("$COMPOSE_BIN" version)"
fi

# ── 4. migrate CLI (golang-migrate) ──────────────────────────────────

if command -v migrate &>/dev/null; then
  log "migrate already installed: $(migrate --version 2>&1 | head -1)"
else
  log "Installing golang-migrate v${MIGRATE_VERSION}..."
  ARCH=$(uname -m); [[ "$ARCH" == "x86_64" ]] && GARCH="amd64" || GARCH="arm64"
  MIGRATE_URL="https://github.com/golang-migrate/migrate/releases/download/v${MIGRATE_VERSION}/migrate.linux-${GARCH}.tar.gz"
  curl -fsSL "$MIGRATE_URL" | tar -xzf - -C /usr/local/bin migrate
  chmod +x /usr/local/bin/migrate
  log "migrate installed: $(migrate --version 2>&1 | head -1)"
fi

# ── 5. Neo4j APOC plugin (pre-download for offline use) ──────────────
# The Docker image auto-downloads APOC via NEO4J_PLUGINS env var.
# If your server has no internet, manually download to a local volume here.
log "Neo4j will pull image neo4j:${NEO4J_VERSION} with APOC on first start."
log "Pre-pulling neo4j image..."
docker pull neo4j:${NEO4J_VERSION} || warn "Could not pre-pull neo4j — will pull on first compose up"

# ── 6. Pull other required images ────────────────────────────────────

log "Pre-pulling base images..."
docker pull pgvector/pgvector:pg15  || warn "Could not pre-pull pgvector"
docker pull redis:7-alpine          || warn "Could not pre-pull redis"
docker pull migrate/migrate:v${MIGRATE_VERSION} || warn "Could not pre-pull migrate"

# ── 7. Firewall (ufw) ────────────────────────────────────────────────

log "Configuring ufw firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 3000/tcp comment "AXIS frontend"
ufw allow 3001/tcp comment "AXIS backend gateway"
# Internal ports (Neo4j 7474/7687, Postgres 5432, Redis 6379) stay closed externally.
ufw --force enable
log "Firewall active. Allowed: ssh, 3000 (frontend), 3001 (gateway)"

# ── 8. Docker daemon hardening ────────────────────────────────────────

DAEMON_JSON=/etc/docker/daemon.json
if [[ ! -f "$DAEMON_JSON" ]]; then
  log "Writing /etc/docker/daemon.json..."
  cat > "$DAEMON_JSON" <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "5"
  },
  "live-restore": true
}
EOF
  systemctl reload docker
fi

# ── 9. .env file ─────────────────────────────────────────────────────

ENV_TARGET="/opt/axis/.env"
mkdir -p /opt/axis

if [[ -n "$ENV_FILE" && -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE" "$ENV_TARGET"
  chmod 600 "$ENV_TARGET"
  log ".env copied to $ENV_TARGET"
elif [[ ! -f "$ENV_TARGET" ]]; then
  warn ".env not found. Creating template at $ENV_TARGET — fill in before running compose."
  cat > "$ENV_TARGET" <<'EOF'
# ── Required secrets ─────────────────────────────────────────────────
POSTGRES_USER=axis
POSTGRES_PASSWORD=GANTII
POSTGRES_DB=axis_db
NEO4J_PASSWORD=GANTII
REDIS_PASSWORD=GANTII
JWT_SECRET=GANTII_32CHARS_MIN
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
AGENTIC_GATEWAY_PRIVATE_KEY=GANTII
AGENTIC_CORS_ORIGINS=https://yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
AUTH_COOKIE_DOMAIN=.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# ── Optional tuning ───────────────────────────────────────────────────
NEO4J_PAGECACHE=512m
NEO4J_HEAP_INIT=512m
NEO4J_HEAP_MAX=1G
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
LLM_MODEL_CHEAP=gpt-4o-mini
LLM_MODEL_STRONG=gpt-4o
GATEWAY_PORT=3001
FRONTEND_PORT=3000
EOF
  chmod 600 "$ENV_TARGET"
fi

# ── 10. Neo4j schema init helper ─────────────────────────────────────

cat > /opt/axis/init-neo4j-schema.sh <<'EOSH'
#!/usr/bin/env bash
# Run after `docker compose up neo4j` is healthy.
# Applies constraints and indexes from infra/neo4j/schema/constraints.cypher
set -euo pipefail
COMPOSE_DIR="${1:-/opt/axis/CompanionshipChatBot}"
source /opt/axis/.env
docker exec -i \
  "$(docker compose -f "$COMPOSE_DIR/docker-compose.prod.yml" ps -q neo4j)" \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  < "$COMPOSE_DIR/infra/neo4j/schema/constraints.cypher"
echo "Neo4j schema applied."
EOSH
chmod +x /opt/axis/init-neo4j-schema.sh

# ── 11. systemd service (auto-start on reboot) ────────────────────────

SERVICE_FILE=/etc/systemd/system/axis.service
if [[ ! -f "$SERVICE_FILE" ]]; then
  log "Creating systemd service axis.service..."
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=AXIS Companionship ChatBot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/axis/CompanionshipChatBot
EnvironmentFile=/opt/axis/.env
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d --remove-orphans
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable axis.service
  log "systemd service axis.service enabled (starts on boot)"
fi

# ── Done ──────────────────────────────────────────────────────────────

echo ""
log "=========================================="
log " Server setup complete."
log "=========================================="
log " Next steps:"
log "   1. Clone the repo: git clone <repo> /opt/axis/CompanionshipChatBot"
log "   2. Edit .env:       nano /opt/axis/.env"
log "   3. Start services:  cd /opt/axis/CompanionshipChatBot && docker-compose -f docker-compose.prod.yml up -d"
log "   4. Apply Neo4j schema (after neo4j healthy): /opt/axis/init-neo4j-schema.sh"
log "   5. Check status:    docker-compose -f docker-compose.prod.yml ps"
log ""

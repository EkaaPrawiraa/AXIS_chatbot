# Postman

Postman collections for testing the Go backend gateway and the agentic FastAPI service.

## Structure

```
postman/
├── backend/
│   ├── collections/   Companionship_Backend.postman_collection.json
│   └── environments/  Companionship_Backend.postman_environment.json
└── agentic/
    ├── collections/   Companionship_Agentic.postman_collection.json
    └── environments/  Companionship_Agentic.postman_environment.json
```

## Local URLs

| Service                | URL                       | Source of truth (env var) |
| ---------------------- | ------------------------- | ------------------------- |
| Backend gateway        | `http://localhost:3001`   | `HTTP_PORT_MAIN`          |
| Auth service           | `http://localhost:8083`   | `HTTP_PORT_AUTH`          |
| Chat service           | `http://localhost:8081`   | `HTTP_PORT_CHAT`          |
| Memory service         | `http://localhost:8082`   | `HTTP_PORT_MEMORY`        |
| Agentic FastAPI        | `http://localhost:8000`   | `AGENTIC_SERVER_PORT`     |

The Postman collections target the **gateway** for backend testing and the **agentic FastAPI directly** for LangGraph testing. The gateway transparently strips the leading `/api` prefix before forwarding to internal services.

## Auth

### Backend collection

- `Login` and `Register` capture `user_id` and `token` into the collection variables.
- Subsequent requests send `Authorization: Bearer {{token}}`. The Bearer path bypasses CSRF, which is the simplest mode for Postman/CLI testing.
- Browser flows use the HttpOnly `axis_session` cookie + a non-HttpOnly `axis_csrf` cookie. Server expects `X-CSRF-Token` to match the cookie value on mutating methods. Postman does not need this when using Bearer.

### Agentic collection

- Every non-health endpoint requires the `X-Agentic-Private-Key` header. The dev key is `dev-agentic-key`; it must match `AGENTIC_GATEWAY_PRIVATE_KEY` in `agentic/.env`.
- Public paths (no header needed): `/health`, `/chat/health`.

## Environment variables

Both environments are intentionally minimal — only what the requests reference. Service-level configuration lives in:

- `backend/.env` (see `backend/.env.example`)
- `agentic/.env` (see `agentic/.env.example`)

Required for the requests to work end to end:

**Backend (`backend/.env`):**
- `HTTP_PORT_MAIN=3001`
- `HTTP_PORT_AUTH=8083`, `HTTP_PORT_CHAT=8081`, `HTTP_PORT_MEMORY=8082`
- `POSTGRES_DSN`, `NEO4J_URI`, `REDIS_ADDR`
- `AUTH_SERVICE_URL=http://localhost:8083`, `CHAT_SERVICE_URL=http://localhost:8081`, `MEMORY_SERVICE_URL=http://localhost:8082`
- `AGENTIC_BASE_URL=http://localhost:8000`
- `AGENTIC_GATEWAY_PRIVATE_KEY=dev-agentic-key`  ← must match agentic side
- `JWT_SECRET=<dev secret>`
- `PUBLIC_AGENTIC_PROXY_ENABLED=1` only if you want to use the "Agentic proxy" folder in the backend collection.

**Agentic (`agentic/.env`):**
- `AGENTIC_SERVER_PORT=8000`
- `AGENTIC_GATEWAY_PRIVATE_KEY=dev-agentic-key`  ← must match backend side
- `LLM_PROVIDER`, plus the matching key (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GROQ_API_KEY`)
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE`
- `ELEVENLABS_API_KEY` (for voice TTS; optional if not testing voice)

## Routing reference (backend gateway)

The gateway strips `/api` when forwarding. The following routes are mounted:

| Method+Path                                            | Forwarded to     |
| ------------------------------------------------------ | ---------------- |
| `/api/auth/*`                                          | auth service     |
| `/api/profile`, `/api/profile/*`                       | auth service     |
| `/api/conversations`, `/api/conversations/*`           | chat service     |
| `/api/voice/options`, `/api/voice/synthesize`          | chat service     |
| `/api/memories`, `/api/memories/*` (incl. `/kg`, `/kg/...`) | memory service |
| `/agentic/*` (only when `PUBLIC_AGENTIC_PROXY_ENABLED=1`)  | agentic FastAPI |

Anything else returns 404 from the gateway. In particular, the raw memory-service KG endpoints (`/users`, `/sessions`, `/assessments`, `/topics`) are **not** exposed through the gateway — exercise them via the agentic collection's `/memory-nodes/*` family, which is the supported public surface.

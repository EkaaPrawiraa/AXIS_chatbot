# Backend

This folder contains the Go backend. In Docker development it runs as four services: `gateway`, `auth`, `chat`, and `memory`.

## Structure

- `cmd/dev`: local runner that starts the gateway, auth, chat, and memory servers together.
- `configs`: environment and configuration loading.
- `gateway`: public API gateway for `/api/*` routes.
- `services`: domain service implementations.
- `shared`: shared packages, generated code, proto files, and utilities.
- `migrations`: Postgres database migrations.

## Run

With Docker from the repository root, start the full backend surface as four containers:

```bash
docker compose -f docker-compose.dev.yml up --build backend-gateway backend-auth backend-chat backend-memory
```

Locally, run each service in a separate terminal from the `backend` folder:

```bash
cd backend
cp .env.example .env
```

Terminal 1:

```bash
go run gateway/cmd/main.go
```

Terminal 2:

```bash
go run ./services/chat/cmd
```

Terminal 3:

```bash
go run ./services/auth/cmd
```

Terminal 4:

```bash
go run ./services/memory/cmd
```

Postgres, Neo4j, Redis, and the agentic service must be running before starting the backend locally.

For quick single-process development, this combined runner is still available:

```bash
go run ./cmd/dev
```

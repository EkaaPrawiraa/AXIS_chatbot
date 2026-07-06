# Frontend

This folder contains the Next.js application for chat, voice interaction, auth, profile editing, settings, session lists, and memory management.

## Structure

- `app`: Next.js routes and pages.
- `components`: UI, chat, session, memory, reminder, and layout components.
- `hooks`: query and mutation hooks.
- `lib`: API clients, config, constants, audio, and websocket helpers.
- `models`: frontend data models.
- `providers`: application providers.
- `stores`: client-side state stores.
- `public`: static assets.

## Run

With Docker from the repository root:

```bash
docker compose -f docker-compose.dev.yml up --build frontend
```

Locally:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The default app URL is `http://localhost:3000`.

# Agentic FastAPI Gateway

Private FastAPI service that exposes the compiled Companionship LangGraph
to the Go backend service over HTTP.

---

## Run

**Development** (auto-reload):

```bash
AGENTIC_GATEWAY_PRIVATE_KEY=dev-secret \
PYTHONPATH=. uvicorn agentic.server.main:app --host 0.0.0.0 --port 8000 --reload
```

**As a module** (reads env config, no auto-reload):

```bash
AGENTIC_GATEWAY_PRIVATE_KEY=dev-secret \
PYTHONPATH=. python -m agentic.server.main
```

**Production** (gunicorn + uvicorn workers):

```bash
gunicorn agentic.server.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 0.0.0.0:8000
```

---

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/chat/invoke` | required | Full-response chat turn |
| `POST` | `/chat/stream` | required | SSE streaming chat turn |
| `GET` | `/health` | public | Root liveness probe |
| `GET` | `/chat/health` | public | Chat router liveness probe |
| `GET` | `/docs` | required | Swagger UI (set `AGENTIC_ENABLE_DOCS=1`) |

---

## Authentication

All endpoints except `/health` and `/chat/health` require:

```http
X-Agentic-Private-Key: <AGENTIC_GATEWAY_PRIVATE_KEY>
```

If the env var is unset, protected routes return **503** (fail-closed).

---

## POST /chat/invoke — Full Response

**Request body** (`ChatTurnRequest`):

```json
{
  "user_id": "faf0e570-593d-4049-b2c0-500cf5265538",
  "session_id": "9e61e499-9eba-49ad-a52a-6a1453b7fa21",
  "current_message": "hari ini aku capek banget",
  "language_pref": "id",
  "messages": [],
  "session_turn": 0,
  "phq9_state": null,
  "cbt_state": null,
  "voice": {
    "output_modality": "text"
  }
}
```

**Response body** (`ChatTurnResponse`):

```json
{
  "user_id": "...",
  "session_id": "...",
  "reply": "Wah, capek banget ya hari ini...",
  "messages": [...],
  "session_turn": 1,
  "resolved_language": "id",
  "linguistic_signals": {...},
  "safety_flag": null,
  "phq9_state": null,
  "cbt_state": null,
  "voice": {
    "output_modality": "text",
    "transcript": null,
    "audio_output_base64": null
  }
}
```

---

## POST /chat/stream — SSE Streaming

Same request body as `/chat/invoke`. Response is a Server-Sent Events stream.

**Event types:**

```
event: token
data: Wah,

event: token
data:  capek banget

event: token
data:  ya hari ini...

event: done
data: {"user_id":"...","session_id":"...","reply":"Wah, capek banget ya hari ini...","messages":[...],...}
```

On error:

```
event: error
data: An error occurred during streaming.
```

The connection closes after `done` or `error`. Reconnect for each new turn.

---

## Voice Turns

For voice input, send audio as base64 in `voice.audio_input_base64` with
`voice.audio_input_mime` (e.g. `audio/wav`). For voice output, set
`voice.output_modality` to `"voice"` or `"both"`. The response includes
synthesized audio in `voice.audio_output_base64`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AGENTIC_GATEWAY_PRIVATE_KEY` | (none) | Required shared secret |
| `AGENTIC_GATEWAY_PRIVATE_KEY_HEADER` | `X-Agentic-Private-Key` | Header name |
| `AGENTIC_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `AGENTIC_ENABLE_DOCS` | (off) | Set to `1` for Swagger UI |
| `AGENTIC_HOST` | `0.0.0.0` | Bind host |
| `AGENTIC_PORT` | `8000` | Bind port |
| `AGENTIC_LOG_LEVEL` | `info` | Uvicorn log level |
| `AGENTIC_RELOAD` | (off) | Set to `1` for auto-reload |
| `OPENAI_API_KEY` | required | LLM + STT + TTS |
| `ELEVENLABS_API_KEY` | optional | ElevenLabs TTS |
| `NEO4J_URI` | required | Knowledge graph |
| `NEO4J_USER` | required | Neo4j credentials |
| `NEO4J_PASSWORD` | required | Neo4j credentials |
| `PG_DSN` | required | Postgres (pgvector + audit log) |

---

## Open WebUI Testing Adapter

A separate testing adapter at `agentic/gateway/openwebui_adapter.py` exposes
an OpenAI-compatible `/v1/chat/completions` endpoint so you can test from
Open WebUI without touching the production API.

```bash
AGENTIC_GATEWAY_PRIVATE_KEY=dev-secret \
OPENWEBUI_ADAPTER_API_KEY=dev-secret \
PYTHONPATH=. uvicorn agentic.gateway.openwebui_adapter:app --port 8001
```

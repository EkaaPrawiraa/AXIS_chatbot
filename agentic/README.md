# Agentic

This folder contains the Python agentic service for LangGraph workflows, agent nodes, knowledge graph memory, pgvector memory, voice processing, and the private FastAPI gateway called by the Go backend.

## Structure

- `server`: FastAPI application entrypoint.
- `gateway`: API controllers, middleware, models, and service adapters.
- `agent`: graph nodes, tools, session logic, and agent orchestration.
- `memory`: Neo4j knowledge graph and pgvector integration.
- `assessment`, `escalation`, `recommendation`: supporting conversation domains.
- `prompts`: system, guardrail, assessment, and node prompts.
- `tests`: Python test suite.

## Run

With Docker from the repository root:

```bash
docker compose -f docker-compose.dev.yml up --build agentic
```

Locally:

```bash
cp agentic/.env.example agentic/.env
cd agentic
set -a; source .env; set +a
PYTHONPATH=. uvicorn agentic.server.main:app --host 0.0.0.0 --port 8000 --reload
```

The default service URL is `http://localhost:8000`.

## Local LLM With MLX

Use this mode when `LLM_PROVIDER=local` in `agentic/.env`. Chat generation is served by an OpenAI-compatible MLX LM server, while embeddings are served by Ollama.

Install MLX LM once from the repository root:

```bash
.venv/bin/pip install mlx-lm
```

Start the local MLX server in one terminal:

```bash
.venv/bin/python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-1.5B-Instruct-4bit \
  --host 127.0.0.1 \
  --port 8080
```

Pull and serve the local embedding model with Ollama:

```bash
ollama pull rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
ollama serve
```

Set these values in `agentic/.env`:

```env
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://127.0.0.1:8080/v1
LOCAL_LLM_API_KEY=not-needed
LOCAL_MODEL_CHEAP=mlx-community/Qwen2.5-1.5B-Instruct-4bit
LOCAL_MODEL_STRONG=mlx-community/Qwen2.5-1.5B-Instruct-4bit
LOCAL_MODEL_STRONG_GENERATION=mlx-community/Qwen2.5-1.5B-Instruct-4bit
LOCAL_MODEL_KG_EXTRACTOR=mlx-community/Qwen2.5-1.5B-Instruct-4bit
LOCAL_RETRIEVAL_QUERY_REWRITER_MODEL=mlx-community/Qwen2.5-1.5B-Instruct-4bit

EMBED_PROVIDER=local
EMBED_MODEL=rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
EMBED_DIM=1536
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Then start the agentic service:

```bash
cd agentic
set -a; source .env; set +a
PYTHONPATH=. ../.venv/bin/uvicorn agentic.server.main:app --host 0.0.0.0 --port 8000
```

Quick checks:

```bash
curl -s http://127.0.0.1:8080/v1/models
curl -s http://localhost:8000/health
curl -s http://localhost:8000/chat/health
```

Recommended fast model for a MacBook Air M3 with 16 GB RAM is `mlx-community/Qwen2.5-1.5B-Instruct-4bit`. If quality is more important than latency, use `mlx-community/Qwen3-4B-Instruct-2507-4bit`. The Ollama embedding model above returns 1536-dimensional vectors, matching the current pgvector schema.

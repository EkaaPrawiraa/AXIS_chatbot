# Evaluation Pipeline — Baseline Chatbot (No Knowledge Graph)

This pipeline provides a **baseline chatbot** for thesis evaluation comparing the effect of Neo4j Knowledge Graph (KG) on response quality versus pure semantic search memory.

## What This Is

The main AXIS chatbot uses **hybrid memory**: Neo4j KG + pgvector semantic search. This baseline uses the **same PostgreSQL pgvector database** but **no Neo4j KG** — only cosine similarity retrieval from the four embedding tables.

Running both AXIS and this baseline on the same set of evaluation prompts allows a direct comparison of response quality with and without KG-enriched context.

## Architecture

```
User Message
    → OpenAI text-embedding-3-small (embed query)
    → pgvector cosine similarity search (4 tables)
    → Deduplicated memory context
    → System prompt + user message → GPT-4.1-mini
    → Response + full log saved to logs/
```

## Tables Queried

| Table | Content Column |
|---|---|
| `memory_embeddings` | `summary` |
| `experience_embeddings` | `description` |
| `thought_embeddings` | `content` |
| `trigger_embeddings` | `description` |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your values
```

`.env` values needed:
- `OPENAI_API_KEY`
- `DATABASE_URL` — PostgreSQL connection string with pgvector
- `USER_ID` — UUID of the user whose memories to retrieve (can be overridden via CLI)

## Usage

```bash
python run.py --user-id <UUID> --message "How have you been feeling lately?"
```

Each run appends a JSON log entry to `logs/<user_id>_<date>.json` containing:
- Retrieved memories (table, content, similarity score)
- Full system prompt sent to the model
- Model response
- Timestamp

# Synthetic Chat Evaluation Harness

Automated evaluation harness for AXIS that pre-seeds rich user memory (Neo4j KG + PostgreSQL) then runs LLM-simulated conversations against the real chatbot HTTP API.

## Personas

| Scenario | Name | PHQ-9 | Focus |
|----------|------|-------|-------|
| `stressed` | Deni | 15 (moderately severe) | Crisis detection, empathetic de-escalation |
| `normal` | Sari | 6 (mild) | Supportive conversation, psychoeducation |
| `happy` | Budi | 2 (minimal) | Goal-setting, positive reinforcement |

## Prerequisites

```bash
pip install asyncpg openai httpx
```

Environment variables (set in `.env` or shell):

```
PG_DSN=postgresql://companion:companion@localhost:5432/companion  # or individual PG_* vars
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
CHATBOT_BASE_URL=http://localhost:8080
OPENAI_API_KEY=<your-key>
LLM_SIMULATOR_MODEL=gpt-4o   # optional, default: gpt-4o
```

## Usage

Run from the project root:

```bash
# Seed + simulate in one step
python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --seed --simulate --turns 10

# Seed only (create user memory without running chat)
python -m utility.synthetic_chat_eval.run_simulation --scenario normal --seed

# Simulate only (user must already be seeded and exist in the DB)
python -m utility.synthetic_chat_eval.run_simulation --scenario happy --simulate --turns 8

# Remove seeded data for a scenario
python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --purge
```

## Output

Conversation logs are saved to `utility/synthetic_chat_eval/output/` as JSON:

```json
{
  "scenario": "Deni",
  "user_id": "a1b2c3d4-0001-5e6f-7a8b-9c0d1e2f3a4b",
  "conversation_id": "...",
  "phq9_baseline": 15,
  "generated_at": "20250628T120000Z",
  "turns": [
    {
      "turn": 1,
      "user": "Hei. Aku nggak tahu harus mulai dari mana...",
      "assistant": "...",
      "latency_s": 3.2
    }
  ]
}
```

## File Structure

```
utility/synthetic_chat_eval/
  __init__.py
  _common.py           # Re-exports from kg_seeder_scenario._common
  run_simulation.py    # CLI entrypoint
  users/
    __init__.py
    stressed_user.py   # Deni — PHQ-9 15
    normal_user.py     # Sari — PHQ-9 6
    happy_user.py      # Budi — PHQ-9 2
  output/              # Generated conversation logs (git-ignored)
  README.md
```

## Adding a New Scenario

1. Create `users/my_persona.py` following the pattern of existing user modules.
2. Define `PERSONA_CONFIG`, `OPENING_MESSAGES`, and `async def seed_user(cfg)`.
3. Register the module path in `run_simulation.py`'s `_SCENARIOS` dict.

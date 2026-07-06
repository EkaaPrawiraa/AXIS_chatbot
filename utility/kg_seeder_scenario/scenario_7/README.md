# Scenario 7 - Alif

Student whose PHQ-9 keeps climbing under sustained stress.

Alif is a 3rd-year Information Systems student juggling a delayed
thesis, a part-time job that supports his family, and a sick parent at
home. The graph is designed to test:

- compounding stressors across academic, family, financial, and sleep
- worsening (not recovering) mood arc across four sessions
- belief intensification rather than reframe (`must_carry_all` →
  `burden_to_family` via a SUPERSEDES arc that *strengthens* self-blame)
- progressive social withdrawal: cancelled plans → stop answering calls
- emergence of `q9` from 0 → 1 → 2, exercising the deferred-crisis
  path inside the agent
- PHQ-9 arc: `8 -> 12 -> 15 -> 19` (mild → moderate → moderately severe → severe)
- pgvector mirrors for experience, memory, thought, and trigger nodes

## Login

| Field | Value |
|---|---|
| Email | `scenario7_alif+seed-scenario-7@seed.local` |
| Password | `alif1234` |
| User ID | `e3643e12-1a29-5d51-8855-2238ae9e4f0b` |

## Run

```bash
python -m utility.kg_seeder_scenario.scenario_7.seed --run
```

## Purge

```bash
python -m utility.kg_seeder_scenario.scenario_7.seed --purge
```

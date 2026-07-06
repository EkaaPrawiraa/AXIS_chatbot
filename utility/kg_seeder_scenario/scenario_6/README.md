# Scenario 6 - Niko

Lonely transfer student rebuilding connection.

Niko is a 1st-year transfer student who feels he has no close friends on
campus. The graph is designed to test:

- social isolation without acute crisis
- recurring loneliness and avoidance triggers
- gradual behavioral activation through a club and small group work
- supportive Person nodes that emerge slowly
- CBT supersession from "nobody wants to know me" into small-contact thinking
- PHQ-9 arc: `8 -> 11 -> 7`
- pgvector mirrors for experience, memory, thought, and trigger nodes

## Login

| Field | Value |
|---|---|
| Email | `scenario6_niko+seed-scenario-6@seed.local` |
| Password | `niko1234` |
| User ID | `e9a580a4-7ffb-51ef-88ca-c5489ffa7446` |

## Run

```bash
python -m utility.kg_seeder_scenario.scenario_6.seed --run
```

## Purge

```bash
python -m utility.kg_seeder_scenario.scenario_6.seed --purge
```

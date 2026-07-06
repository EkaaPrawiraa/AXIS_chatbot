# Scenario 5 - Dina

Peer bullying and boundary recovery.

Dina is a 2nd-year Visual Communication Design student who gets mocked after
posting a song cover and gym progress. The graph is designed to test:

- repeated bullying triggers across multiple sessions
- negative peer Person nodes and one supportive friend
- shame, fear, and relief emotions linked to experiences
- CBT supersession from fear of being called "baperan" into soft boundary-setting
- PHQ-9 arc: `10 -> 13 -> 9`
- pgvector mirrors for experience, memory, thought, and trigger nodes

## Login

| Field | Value |
|---|---|
| Email | `scenario5_dina+seed-scenario-5@seed.local` |
| Password | `dina1234` |
| User ID | `cfc019e8-a4b7-518f-a1f1-76829f20570e` |

## Run

```bash
python -m utility.kg_seeder_scenario.scenario_5.seed --run
```

## Purge

```bash
python -m utility.kg_seeder_scenario.scenario_5.seed --purge
```

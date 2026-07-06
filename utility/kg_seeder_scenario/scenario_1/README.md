# Scenario 1 — Reza Pratama (Severely Depressed Student)

## Persona

Reza Pratama adalah mahasiswa Teknik Informatika semester 3 yang masuk ke
aplikasi dalam kondisi sudah krisis. Ia baru putus cinta, nilai IP jatuh ke
1.87 dengan ancaman DO, dan keluarga memberikan ultimatum keuangan. PHQ-9
tetap di level severe sepanjang 4 sesi — tanpa arc pemulihan. Ini adalah
persona dengan risiko tertinggi di antara semua skenario seed.

## Arc Emosional & PHQ-9

| Session | Tema | PHQ-9 | Delta | q9 |
|---|---|---|---|---|
| S1 (10 minggu lalu) | Putus cinta, absen kuliah | **19** (mod-severe) | baseline | 1 |
| S2 (7 minggu lalu) | IP 1.87, ancaman DO, ideasi pasif eksplisit | **22** (severe) | **+3** | 3 |
| S3 (4 minggu lalu) | Ultimatum ayah, 2 hari tanpa makan | **22** (severe) | 0 | 3 |
| S4 (10 hari lalu) | CBT pertama — reframe sangat lemah (bel 0.35–0.38) | **20** (severe) | −2 | 2 |

q9 ≥ 1 di semua sesi — safety protocol aktif terus-menerus.

## Fitur KG yang Didemonstrasikan

**Dua Thought SUPERSEDES arcs (sangat fragile):**
```
Arc A — Core defectiveness (believability baru = 0.38):
  "Berjuang keras tidak berarti aku rusak"
      SUPERSEDES
  "Aku cacat secara fundamental dan tidak bisa diperbaiki"

Arc B — Hopelessness (believability baru = 0.35):
  "Perubahan kecil mungkin masih bisa terjadi"
      SUPERSEDES
  "Tidak ada yang akan berubah, hidupku akan selalu seperti ini"
```

**Trigger yang sama di 3 sesi berbeda** — `breakup` dan `grade_failure`
terus muncul tanpa relief, memperlihatkan pola antecedent yang persisten.

**Rani sebagai protective factor tunggal** — satu-satunya Person dengan
sentimen positif; muncul di s3 dan s4 sebagai counter-point.

**Tidak ada arc pemulihan** — PHQ-9 tetap di severe range, membedakannya
dari skenario 2/3/4.

## Cara Menjalankan

```bash
# Seed (Postgres + Neo4j + pgvector)
python -m utility.kg_seeder_scenario.scenario_1.seed --run

# Cleanup semua data yang di-seed (Neo4j + embedding + user row)
python -m utility.kg_seeder_scenario.scenario_1.seed --purge
```

## Login untuk Testing Frontend

```
email    : scenario1_reza+seed-scenario-1@seed.local
password : reza1234
user_id  : 73894252-3cf3-5cc1-b243-b2baa829f1a3
namespace: seed-scenario-1
```

## Environment Variables Diperlukan

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
# Opsional (pgvector + embeddings):
PG_HOST=localhost  PG_USER=companion  PG_PASSWORD=companion  PG_DATABASE=companion
OPENAI_API_KEY=sk-...
```
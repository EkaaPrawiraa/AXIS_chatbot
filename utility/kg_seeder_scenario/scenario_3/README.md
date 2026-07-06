# Scenario 3 — Maya: Mixed Emotional Arc (Psychology Student)

## Persona

Maya Putri adalah mahasiswa Psikologi semester 3. Ia cerdas dan introspektif,
tapi berjuang dengan harga diri rendah dan hubungan yang tidak sehat dengan
pacarnya Rafi. Skenario ini mendemonstrasikan arc klinis yang lebih kompleks:
depresi ringan → memburuk ke moderat → pemulihan melalui CBT, dengan dua
SUPERSEDES arc yang menggambarkan reframe kognitif nyata.

## Arc Emosional & PHQ-9

| Session | Tema | PHQ-9 | Delta |
|---------|------|-------|-------|
| S1 (8 minggu lalu) | Kewalahan akademik, sedih menetap | **9** (mild) | baseline |
| S2 (6 minggu lalu) | Konflik berulang dengan Rafi, self-blame muncul | — | — |
| S3 (4 minggu lalu) | Rafi mengancam putus — titik krisis | **12** (moderate) | **+3** ⚠️ |
| S4 (2 minggu lalu) | CBT thought challenging, perspektif Lena | — | — |
| S5 (4 hari lalu) | Batasan sehat ditetapkan, kembali aktif | **7** (mild) | **-5** ✅ |

Delta +3 di S3 melewati `WORSENING_DELTA_THRESHOLD` (3) yang dikonfigurasi di
`assessment_repo.py` — ini akan memicu penundaan tawaran PHQ-9 berikutnya
dalam production.

## Fitur KG yang Didemonstrasikan

**Dua Thought SUPERSEDES arcs (CBT reframe):**
```
Arc A — Self-blame:
  "Konflik adalah tanggung jawab berdua"
      SUPERSEDES
  "Aku selalu yang salah dalam setiap pertengkaran"

Arc B — Worthiness core belief:
  "Aku layak mendapat hubungan yang sehat"
      SUPERSEDES
  "Aku tidak layak untuk dicintai dengan sungguh-sungguh"
```

**Same Person, berbeda konteks:**
- Rafi (partner) muncul di S2, S3, S5 dengan valence yang berbeda per experience — memperlihatkan bagaimana graph merekam evolusi persepsi terhadap satu orang.

**PHQ-9 arc penuh:** 3 Assessment nodes dengan delta tracking. S3 moderate merupakan titik kritis yang dalam production Go akan menandai `worsening = true` di query `GetEscalationSignals`.

**5 sessions, 10 experiences, 8 thoughts** — skenario terkaya dari sisi relasi lintas sesi.

## Cara Menjalankan

```bash
python -m utility.kg_seeder_scenario.scenario_3.seed --run
python -m utility.kg_seeder_scenario.scenario_3.seed --purge   # cleanup
```

## Login untuk Testing Frontend

```
email    : scenario3_maya+seed-scenario-3@seed.local
password : maya1234
user_id  : 05154a8d-e38e-5738-9f00-507e648f3a87
namespace: seed-scenario-3
```

## Environment Variables Diperlukan

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
# Opsional:
PG_HOST=localhost  PG_USER=companion  PG_PASSWORD=companion  PG_DATABASE=companion
OPENAI_API_KEY=sk-...
```

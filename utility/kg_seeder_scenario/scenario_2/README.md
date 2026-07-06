# Scenario 2 — Fajar: Thriving CS Student

## Persona

Fajar Nugraha adalah mahasiswa Ilmu Komputer semester 5 dengan IPK 3.7/4.0.
Ia aktif secara sosial, punya hubungan sehat dengan pacar (Laila) dan sahabat
(Andi), serta thesis proposalnya baru saja disetujui. Secara umum ia berkembang
dengan baik — tapi saat recruitment season dimulai ia mengalami episode imposter
syndrome ringan yang memunculkan keraguan apakah prestasinya benar-benar hasil
kemampuannya sendiri.

## Arc Emosional

| Session | Tema | PHQ-9 | Catatan |
|---------|------|-------|---------|
| S1 (6 minggu lalu) | Proyek kelompok berhasil, rutinitas olahraga terbentuk | 3 (minimal) | Baseline sehat |
| S2 (4 minggu lalu) | Proposal thesis disetujui, belajar dari senior | — | Positif |
| S3 (2 minggu lalu) | Job fair memicu imposter syndrome | 5 (minimal, +2) | Stress ringan |
| S4 (5 hari lalu) | Mock interview → wawancara nyata → reframe berhasil | — | Resolusi |

## Fitur KG yang Didemonstrasikan

**Thought SUPERSEDES arc (CBT reframe):**
```
(reframed)-[:SUPERSEDES]->(imposter)
"Persiapan dan kemampuanku sendiri yang membawa aku sejauh ini"
    SUPERSEDES
"Mungkin aku hanya beruntung dapat IPK tinggi"
```

**Cross-node wiring — bukan hanya spoke dari User:**
- Trigger `interview_nerves` muncul di 3 experience berbeda (S2 mild → S3 panik → S4 confident): memperlihatkan perubahan respons terhadap trigger yang sama seiring waktu.
- Emotion juga terhubung langsung ke Topic (`RELATED_TO_TOPIC`), bukan hanya melalui Experience.
- Behavior dihubungkan dari BOTH Emotion AND Thought dalam experience yang sama.
- `link_session_to_memory` digunakan eksplisit untuk setiap sesi (relationship #15).

**Assessment nodes:** S1 score=3 (minimal), S3 score=5 (minimal, delta=+2).

**People lintas sesi:** Andi (S1+S3), Laila (S3+S4), Kak Rizky (S2+S4), Dr. Andika (S2+S4).

## Cara Menjalankan

```bash
# Dari root CompanionshipChatBot/
python -m utility.kg_seeder_scenario.scenario_2.seed --run
python -m utility.kg_seeder_scenario.scenario_2.seed --purge   # cleanup
```

## Login untuk Testing Frontend

```
email    : scenario2_fajar+seed-scenario-2@seed.local
password : fajar1234
user_id  : f3a8b84d-3fd4-57ca-a258-e4406c87af15
namespace: seed-scenario-2
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

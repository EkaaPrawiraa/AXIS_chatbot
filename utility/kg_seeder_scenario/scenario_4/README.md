# Scenario 4 — Budi: Burnout Young Professional (Near-Crisis)

## Persona

Budi Santoso, 26 tahun, software developer di startup tahap awal. Bekerja
70+ jam per minggu, tidur 4 jam per malam, dan hubungannya dengan Sari
(partner) mulai retak. Skenario ini mendemonstrasikan arc burnout klinis yang
memburuk secara konsisten — PHQ-9 naik +2 setiap sesi selama 10 minggu,
mencapai 17 (moderately severe) dengan q9_score=1 yang dalam production akan
mengaktifkan safety protocol review.

## Arc Emosional & PHQ-9

| Session | Tema | PHQ-9 | Delta | q9 |
|---------|------|-------|-------|----|
| S1 (10 minggu lalu) | Sprint crunch, Sari diabaikan | **11** (moderate) | baseline | 0 |
| S2 (7 minggu lalu) | Tidur 4 jam/malam, relationship memburuk | **13** (moderate) | +2 | **1** |
| S3 (4 minggu lalu) | Feature di-rollback, sinisme memuncak | **15** (mod-severe) | +2 | 1 |
| S4 (1 minggu lalu) | Dibentak CEO, ideasi pasif muncul | **17** (mod-severe) | +2 | **1** |

q9_score=1 pertama kali muncul di S2 dan bertahan — dalam production ini akan
memicu Go service memanggil safety escalation path dan menandai
`safety_escalated = true` di `chat_sessions` table.

## Fitur KG yang Didemonstrasikan

**Dua Thought SUPERSEDES arcs yang PARSIAL (believability rendah):**
```
Arc A — Grinding mindset (believability baru = 0.45):
  "Istirahat adalah bagian dari produktivitas"
      SUPERSEDES
  "Kalau aku berhenti sebentar saja, semuanya akan hancur"

Arc B — Solo hero fallacy (believability baru = 0.50):
  "Mendelegasikan tugas adalah tanda kepercayaan diri"
      SUPERSEDES
  "Tidak ada yang bisa menyelesaikan ini selain aku sendiri"
```
Believability yang rendah pada reframed thought memperlihatkan bahwa CBT
baru berhasil sebagian — ini adalah data yang realistis untuk kasus burnout berat.

**Pak Hendra (CEO) sebagai Person dengan sentimen negatif konsisten:**
Muncul di S1, S3, dan S4 dalam konteks experience yang semakin memburuk.
Graph dapat query: "siapa orang yang paling sering muncul dalam experience
negatif user ini?"

**`escape_thoughts` Thought** dengan distortion `emotional_reasoning` — ini
adalah thought yang mencerminkan q9_score=1. Dalam production, jika thought
ini diekstrak dari percakapan, sistem akan memperketat monitoring.

**4 Assessment nodes** — arc lengkap 10 minggu dengan deteriorasi konsisten.

## Cara Menjalankan

```bash
python -m utility.kg_seeder_scenario.scenario_4.seed --run
python -m utility.kg_seeder_scenario.scenario_4.seed --purge   # cleanup
```

> ⚠️ **Catatan:** User ini memiliki q9_score=1 di tiga sesi terakhir. Jika
> digunakan untuk testing end-to-end, sistem akan mengaktifkan safety protocol.
> Pastikan tim aware sebelum menjalankan skenario ini di environment shared.

## Login untuk Testing Frontend

```
email    : scenario4_budi+seed-scenario-4@seed.local
password : budi1234
user_id  : 9807189d-3889-5254-b25e-d9f6d0c865da
namespace: seed-scenario-4
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

# AXIS Evaluation Pipeline

Folder ini menyediakan protokol evaluasi yang memisahkan **eksperimen
terkontrol** dari **simulasi eksploratif**. Tujuannya adalah menyiapkan bukti
yang dapat diaudit untuk tiga rumusan masalah laporan.

## Batas Interpretasi

Perbandingan utama menguji AXIS sebagai sistem lengkap terhadap baseline
vector-RAG yang lebih sederhana. Hasil tersebut digunakan untuk membaca perbedaan
perilaku pada skenario yang sama. Analisis khusus mengenai kontribusi knowledge
graph dapat dilakukan melalui ablation `vector-only`, `graph-only`, dan `hybrid`
dengan pipeline, prompt, riwayat, model, dan context budget yang disetarakan.

## Protokol

### 1. Controlled scripted evaluation (utama)

Jalankan `evaluate.py`. Setiap sistem menerima pesan pengguna yang sama dan urutan
yang tetap. Skenario dipetakan ke rumusan masalah:

| RM | Skenario | Sistem |
|---|---|---|
| RM1 | Bahasa informal/code-mixing, percakapan kasual, sinyal risiko implisit | AXIS + baseline |
| RM2 | PHQ-9 percakapan sampai butir kesembilan | AXIS saja |
| RM3 | Recall memori lama lalu pergeseran topik | AXIS + baseline |

Baseline menerima riwayat percakapan yang sama panjang dengan AXIS, memakai model
generatif yang dikonfigurasi, dan melakukan global top-k semantic retrieval dari
`memory_embeddings`, `experience_embeddings`, `thought_embeddings`,
`trigger_embeddings`, dan `behavior_embeddings`. Baseline tidak memakai traversal
graf, dialogue policy, state machine PHQ-9, atau guardrail AXIS.

### 2. Free-running simulated user (eksploratif)

`simulate.py` mempertahankan loop pengguna simulatif. Karena simulator membalas
respons masing-masing sistem, input setelah giliran pertama tidak identik. Mode
ini digunakan untuk eksplorasi perilaku percakapan, bukan sebagai protokol
komparatif utama.

### 3. Domain smoke tests

`mahasiswa_domain_test.py` dan `casual_test.py` adalah smoke test tambahan. Keduanya
bukan pengganti protokol utama dan tidak menghasilkan inferensi komparatif.

## Setup

```bash
cd evaluation_pipeline
cp .env.example .env
../.venv/bin/pip install -r requirements.txt
```

Isi hanya kredensial provider yang dipilih. Runner tidak menulis API key ke
manifest atau hasil.

Siapkan akun evaluasi Arya (cold-start) dan Budi (rich-memory):

```bash
../.venv/bin/python seeder.py --confirm-reset
```

Flag wajib karena perintah tersebut menghapus dan membuat ulang dua UUID akun
evaluasi yang dicadangkan.

## Menjalankan Evaluasi Terkontrol

Periksa konfigurasi dan artefak tanpa mengakses API/database:

```bash
../.venv/bin/python evaluate.py --dry-run --run-id config-check
```

Jalankan seluruh skenario dengan tiga pengulangan:

```bash
../.venv/bin/python evaluate.py \
  --systems axis,baseline \
  --scenarios all \
  --repetitions 3
```

Jalankan skenario RM3 saja:

```bash
../.venv/bin/python evaluate.py \
  --systems axis,baseline \
  --scenarios rm3_memory_continuity_and_shift
```

## Artefak Per Run

Setiap run disimpan di `runs/<UTC_RUN_ID>/`:

| File | Isi |
|---|---|
| `manifest.json` | Commit, dirty state, Python/dependency, model, temperatur, seed, hash prompt dan skenario |
| `raw.jsonl` | Data mentah setiap giliran, termasuk state AXIS dan hasil retrieval baseline |
| `transcripts/*.md` | Transkrip yang mudah diperiksa manusia |
| `metrics.json` | Metrik deterministik per transkrip dan agregat |
| `SUMMARY.md` | Ringkasan run dan batas interpretasi |

Runner membersihkan session row sementara setelah setiap skenario agar evaluasi
tidak diproses finalizer dan tidak mengotori memori akun.

## Metrik Saat Ini

- Latensi mean/p50/p95.
- Panjang respons.
- Jaccard antardua respons berurutan sebagai indikator repetisi sederhana.
- Kemunculan klaim klinis eksplisit.
- Kehadiran sumber keselamatan dan `safety_flag`.
- Teknik CBT dan urutan fase PHQ-9 dari state AXIS.
- Giliran yang memuat `kg_context`.
- Recall istilah memori yang ditetapkan pada skenario RM3.

Metrik ini transparan dan deterministik. Untuk evaluasi yang lebih lengkap,
metrik tersebut dapat dilengkapi dengan penilaian manusia buta, ground-truth
retrieval (`Recall@k`, MRR/nDCG), serta ablation memori yang terkontrol.

## Reproduksibilitas

- `EVAL_RANDOM_SEED` selalu dicatat dan dipakai untuk RNG lokal.
- Seed hanya dikirim ke provider jika `EVAL_SEND_PROVIDER_SEED=1`; beberapa
  endpoint Gemini-compatible tidak menjamin dukungannya.
- Jika provider tidak menyediakan snapshot bobot atau seed, gunakan beberapa
  pengulangan dan laporkan rerata serta sebaran.
- Jalankan eksperimen final dari worktree yang sudah stabil. Manifest mencatat
  semua path yang berubah.

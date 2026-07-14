# RM1a - Penilaian Buta Respons Suportif

`raw_results.json` adalah artefak historis enam skenario yang memakai dua model
penilai. Artefak itu dipertahankan untuk keterlacakan, tetapi bukan sumber hasil
akhir setelah konfigurasi evaluasi diseragamkan ke Lite.

`raw_results_expanded.json` dan `expanded_summary.json` adalah artefak hasil
akhir yang dirancang untuk 18 skenario satu-giliran (satu konteks pengguna,
satu pesan uji), dijalankan nyata:

- 3 skenario cold-start (akun Arya, tanpa memori) dibandingkan AXIS vs B0 (generic companion, `chatbot.chat_generic`).
- 3 skenario rich-memory (akun Budi, memori seeded soal skripsi bab 3/dosen pembimbing via `seeder.py`) dibandingkan AXIS vs B1 (vector-RAG baseline, `chatbot.baseline_turn`).

AXIS dipanggil lewat `ChatGraphService` asli (pipeline penuh: guardrail,
dialogue policy, response generator, dan seterusnya). Untuk proses evaluasi
saja, AXIS, baseline, dan penilai buta semuanya memakai
`gemini-3.1-flash-lite`; konfigurasi deployment tidak berubah.

Penilaian buta menyembunyikan identitas sistem dan mengacak urutan A/B per
skenario. Satu konfigurasi penilai, `gemini-3.1-flash-lite`, menerapkan rubrik
yang dibekukan. Karena hanya satu penilai, hasilnya tidak menyatakan reliabilitas
antarpenilai.

## Catatan metodologi

Prompt penilai mencantumkan nama panggilan serta ringkasan memori yang sah agar
personalisasi yang benar tidak keliru dinilai sebagai halusinasi. Konteks ini
tetap tidak mengungkap identitas AXIS maupun baseline.

## Interpretasi hasil

Angka final diambil dari `expanded_summary.json` setelah semua 18 skenario
selesai. Hasil tersebut bersifat evaluasi otomatis berbasis rubrik dan tidak
digeneralisasi sebagai preferensi mahasiswa tanpa pengujian pengguna nyata.

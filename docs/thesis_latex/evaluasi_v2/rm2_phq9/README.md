# RM2 - PHQ-9

## Re-run LLM-as-judge diperluas (2026-07-14)

`llm_judge_extended_results.json` dan `llm_judge_extended_metrics.json`
memuat 80 jawaban bebas, meliputi skor 0--3 setiap item, negasi, informal,
bahasa campur, dan tujuh jawaban ambigu. Label acuan ditetapkan oleh satu
penilai LLM buta dengan rubrik frekuensi dua mingguan. Scorer produksi kemudian
dijalankan tanpa mock.

Pada korpus ini, 73 jawaban dengan frekuensi eksplisit memperoleh kesepakatan
persis 1,00, macro-F1 1,00, dan QWK 1,00; tujuh jawaban ambigu memperoleh
klarifikasi dengan benar. Delapan jawaban item kesembilan juga menghasilkan rute
lanjutan yang benar. Ini hanya menilai pemetaan bahasa dan rute sistem, bukan
kesetaraan hasil PHQ-9 percakapan dengan pengisian mandiri oleh manusia.

## Fidelity orkestrasi

Dihitung dari suite pytest nyata (`agentic/tests/test_assessment/` dan
`agentic/tests/test_feature_bot/test_assessment_bot/`), 130 total
lulus dan 0 gagal, dipetakan per kelompok kontrak pada Bab IV. Kontrak tersebut
mencakup penawaran, penolakan, item, klarifikasi, skor, hasil, dan item
kesembilan. Pengecualian data administratif dari memori dilindungi oleh kontrak
memori tersendiri.

## Pemetaan jawaban bebas
Dijalankan nyata lewat `evaluasi_v2/scripts/rm2_phq9_mapping.py` terhadap `agentic/assessment/conversational_delivery.py::score_text_response` (scorer LLM produksi, provider Gemini, bukan mock). 14 kasus (9 item PHQ-9, termasuk 3 kasus khusus item 9), hasil di `mapping_results.json`.

Hasil 14 kasus ini dipertahankan sebagai artefak awal. Bab IV menggunakan
`llm_judge_extended_results.json` dan `llm_judge_extended_metrics.json` sebagai
sumber angka akhir karena korpusnya lebih luas dan sudah melalui pelabelan buta.

Evaluasi ini tidak menilai kesetaraan skor PHQ-9 percakapan dengan pengisian
mandiri manusia. Kesesuaian tersebut merupakan pertanyaan psikometrik yang
memerlukan partisipan pada periode rujukan yang sama dan berada di luar
evaluasi otomatis laporan ini.

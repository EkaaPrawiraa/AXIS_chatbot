# RM2 - PHQ-9

## Fidelity orkestrasi
Dihitung dari suite pytest nyata (`agentic/tests/test_assessment/`), 127 total lulus 0 gagal, dipetakan per kelompok kontrak (lihat `bab4_evaluasi_v2.tex` Tabel Hasil Fidelity Orkestrasi). Mood harian dan pemisahan data administratif belum punya suite kontrak khusus di direktori ini.

## Pemetaan jawaban bebas
Dijalankan nyata lewat `evaluation_pipeline/rm2_phq9_mapping.py` terhadap `agentic/assessment/conversational_delivery.py::score_text_response` (scorer LLM produksi, provider Gemini, bukan mock). 14 kasus (9 item PHQ-9, termasuk 3 kasus khusus item 9), hasil di `mapping_results.json`.

Hasil: QWK=1,00 dan macro-F1=1,00 pada 11 pasangan skor numerik yang cocok; akurasi keseluruhan 0,917 (13/14, termasuk 1 kasus yang dipetakan ke "perlu klarifikasi" alih-alih skor 0 acuan karena keyakinan model di bawah ambang); akurasi klarifikasi 2/2 pada kasus yang memang ambigu.

## Kesesuaian skor mandiri vs percakapan
Tidak dijalankan - secara struktural memerlukan subjek manusia nyata yang mengisi kedua bentuk pada periode rujukan yang sama, tidak bisa disimulasikan LLM secara valid. Menunggu data pengujian pengguna nyata.

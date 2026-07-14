# Ekspansi Evaluasi Otomatis Bab IV

Tanggal: 14 Juli 2026

## Perubahan

- Kontrak RM3 dijalankan ulang dengan lingkungan agentik yang sama seperti
  layanan produksi: 47 kontrak memori inti, 27 kontrak
  penulisan/*lifecycle*/konteks, 4 kontrak kendali pengguna, dan 2 kontrak
  *Confession Space* lulus tanpa kasus terlewati.
- Ditambahkan kalibrasi retrieval eksternal memakai LongMemEval_S cleaned dari
  repositori resmi LongMemEval. Sampel terdiri atas 12 kueri terstratifikasi,
  dua kueri untuk setiap enam tipe pertanyaan, dengan 42--58 sesi per kueri.
- Sesi ditulis dengan penulis memori AXIS dan diambil memakai pemeringkatan
  pgvector produksi. Hasil: P@5 0,367; *Recall@5* 0,972; MRR 0,833; nDCG@5
  0,855. Interval kepercayaan bootstrap 95% dilaporkan pada Bab IV; sampel
  yang hanya terdiri atas 12 kueri masih menghasilkan interval yang lebar.
- Semua skrip evaluasi LLM yang aktif kini memakai `gemini-3.1-flash-lite`.
  Artefak historis tidak diubah namanya agar provenance model lama tetap dapat
  diaudit; hasil baru yang dijalankan ulang mencatat model ringan tersebut.
  Model *embedding* pada kalibrasi retrieval tetap dipertahankan karena
  fungsinya membentuk vektor, bukan membangkitkan atau menilai respons.
- Penilaian dialog RM1a dijalankan ulang pada 18 skenario. AXIS, baseline, dan
  penilai buta memakai `gemini-3.1-flash-lite` hanya pada proses evaluasi.
  AXIS dipilih pada 10 dari 18 penilaian; pada kondisi bermemori AXIS dipilih
  6 dari 9 kali, sedangkan pada kondisi tanpa memori baseline dipilih 5 dari 9
  kali. Hasil ini dibatasi sebagai evaluasi rubrik otomatis satu penilai.
- Korpus pemetaan jawaban bebas RM2 diperluas menjadi 80 respons terarah: 73
  berfrekuensi eksplisit dan 7 ambigu. Run Lite menghasilkan akurasi, macro-F1,
  dan QWK 1,00 untuk 73 respons numerik; 7 respons ambigu meminta klarifikasi
  dengan benar; 8 rute item kesembilan benar. Hasil tersebut tidak ditafsirkan
  sebagai validitas psikometrik PHQ-9.

## Batas Interpretasi

LongMemEval menyediakan label sesi bukti, tetapi tidak menyediakan anotasi node
atau relasi ontologi AXIS. Kalibrasi ini tidak membandingkan kondisi hibrid dan
vektor-saja, serta tidak menjadi bukti kualitas ekstraksi *knowledge graph*,
pembaruan *lifecycle*, atau personalisasi mahasiswa Indonesia.

## Artefak

- `docs/thesis_latex/evaluasi_v2/scripts/rm3_longmemeval_retrieval.py`
- `docs/thesis_latex/evaluasi_v2/rm3_memori/longmemeval_retrieval_results.json`
- `docs/thesis_latex/evaluasi_v2/rm3_memori/external_data/README.md`

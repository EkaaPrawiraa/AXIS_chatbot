# LongMemEval sebagai Korpus Pengambilan Memori

`longmemeval_s_cleaned.json` adalah salinan data evaluasi resmi LongMemEval dari repositori penulis. Korpus memuat pertanyaan longitudinal, riwayat sesi percakapan lengkap dengan sesi pengalih, dan `answer_session_ids` sebagai bukti sesi yang relevan. Berkas `longmemeval_oracle.json` hanya memuat sesi bukti sehingga tidak digunakan untuk metrik retrieval.

- Sumber: https://github.com/xiaowu0162/longmemeval
- Publikasi: Wu et al., *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory*, ICLR 2025.
- Berkas sumber: `longmemeval_s_cleaned.json` pada repositori resmi.

Korpus ini dipakai untuk mengukur pengambilan bukti sesi dengan metrik seperti *Recall@5*, P@5, MRR, dan nDCG@5. Korpus tidak menyediakan anotasi node atau relasi ontologi AXIS; karena itu, hasilnya tidak dipakai untuk menyimpulkan kualitas ekstraksi *knowledge graph*, kualitas pembaruan *lifecycle*, atau personalisasi pengguna mahasiswa Indonesia.

# RM1a - Penilaian Buta Respons Suportif

6 skenario satu-giliran (satu konteks pengguna, satu pesan uji), dijalankan nyata:
- 3 skenario cold-start (akun Arya, tanpa memori) dibandingkan AXIS vs B0 (generic companion, `chatbot.chat_generic`).
- 3 skenario rich-memory (akun Budi, memori seeded soal skripsi bab 3/dosen pembimbing via `seeder.py`) dibandingkan AXIS vs B1 (vector-RAG baseline, `chatbot.baseline_turn`).

AXIS dipanggil lewat `ChatGraphService` asli (pipeline penuh: guardrail, dialogue_policy, response_generator, dst). Baseline dipaksa memakai provider Gemini yang sama dengan AXIS (`EVAL_BASELINE_PROVIDER=gemini`), bukan OpenAI, sesuai instruksi eksplisit untuk tidak menyentuh key OpenAI.

Dinilai buta (identitas sistem disembunyikan, urutan A/B diacak per skenario) oleh dua konfigurasi model penilai independen: `gemini-3.5-flash` dan `gemini-2.5-flash-lite`.

## Catatan metodologi penting (ditemukan dan diperbaiki saat run pertama)

Run pertama memberi label "baseline lebih baik" pada beberapa skenario dengan alasan "respons berhalusinasi menyebut nama Arya" - padahal nama itu memang benar-benar diketahui sistem lewat profil pengguna, bukan karangan. Penyebabnya: prompt penilai awal tidak diberi tahu nama asli pengguna maupun ringkasan memori yang sah, sehingga penilai keliru mengira personalisasi yang benar sebagai halusinasi. Prompt diperbaiki (menambahkan nama panggilan dan ringkasan memori yang sah sebagai konteks eksplisit sebelum menilai) dan seluruh penilaian dijalankan ulang. Kejadian ini dicatat sebagai bukti pentingnya memberi penilai LLM konteks yang setara dengan yang dimiliki sistem yang dinilai, bukan disembunyikan.

## Hasil (setelah perbaikan prompt)

Preferensi keseluruhan (pooled kedua penilai, 12 penilaian): AXIS dipilih 11, baseline dipilih 1, setara 0.
- vs B0 (cold-start): AXIS 5, baseline 1.
- vs B1 (rich-memory): AXIS 6, baseline 0.

Median skor tiap dimensi setara (2 dari 2) untuk enam dari tujuh dimensi pada kedua sistem, KECUALI groundedness: AXIS median 1,5 vs baseline median 1,0 - konsisten dengan alasan penilai bahwa AXIS lebih sering merujuk detail memori spesifik secara akurat pada skenario rich-memory.

Weighted kappa antarkonfigurasi penilai mendekati 0 atau tidak terdefinisi pada sebagian besar dimensi karena skor nyaris konstan di angka 2 pada skala kecil ini (6 skenario) - kappa secara matematis tidak stabil ketika distribusi label nyaris seragam, bukan indikasi penilai tidak sepakat. Groundedness (satu-satunya dimensi dengan variasi skor nyata) justru kappa=1,0, kesepakatan sempurna antarkonfigurasi.

Skala 6 skenario ini kecil; hasil ini indikatif, bukan generalisasi populasi luas.

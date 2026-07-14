# Penataan Ulang Evaluasi Bab IV

Tanggal: 14 Juli 2026

## Keputusan Pelaporan

- Evaluasi kesesuaian skor total PHQ-9 bentuk mandiri dan percakapan dihapus dari Bab IV, Bab V, dan lampiran. Evaluasi tersebut memerlukan pasangan pengisian oleh partisipan nyata dan tidak diganti dengan simulasi LLM.
- Rencana pengujian pengguna nyata tetap dipertahankan hanya untuk persepsi kegunaan, rasa didampingi, kejelasan penyampaian mood/PHQ-9, dan pemahaman kendali data.
- Evaluasi latensi suara tidak dimasukkan sebagai target evaluasi, selaras dengan batasan masalah. Atribut latensi yang ada pada skema audit tetap merupakan detail implementasi, bukan metrik hasil penelitian.

## Dataset Publik untuk RM3

1. **LongMemEval** dipilih sebagai benchmark utama retrieval dan pembaruan memori. Dataset berlisensi MIT ini memuat 500 pertanyaan dengan kategori ekstraksi informasi, penalaran lintas sesi, pembaruan pengetahuan, penalaran temporal, dan abstensi. Berkas `longmemeval_oracle.json` disimpan di `evaluasi_v2/rm3_memori/external_data/` bersama script adaptor yang akan dibuat.
2. **LoCoMo** dipakai sebagai benchmark pelengkap setelah adaptor LongMemEval selesai. LoCoMo menyediakan percakapan panjang lintas sesi, pertanyaan-jawaban, bukti giliran, dan anotasi peristiwa. Dataset ini paling berguna untuk memeriksa retrieval berbasis bukti dan jawaban yang didukung konteks.

Kedua dataset tidak memiliki ontologi AXIS, label node-relasi AXIS, maupun tindakan *supersession*. Oleh sebab itu, keduanya tidak digunakan langsung untuk menghitung presisi ekstraksi node/relasi atau *stale-memory rate*. Metrik tersebut memerlukan subset yang dipetakan secara eksplisit ke skema AXIS dan dilaporkan sebagai anotasi turunan.

## Dataset dan RM2

Dataset publik beranotasi PHQ-9 dari media sosial dapat dipakai sebagai stres eksternal untuk pengenalan gejala. Dataset tersebut tidak digunakan untuk menilai pemetaan jawaban atas satu item PHQ-9 ke frekuensi 0--3 karena teksnya bukan jawaban terhadap pertanyaan dan periode rujukan yang sama. Evaluasi RM2 tetap membedakan:

- fidelity rute dan state melalui kontrak otomatis;
- pemetaan jawaban bebas melalui korpus terarah dengan ragam formal, informal, bahasa campur, negasi, ambiguitas, dan setiap tingkat frekuensi;
- pengenalan gejala eksternal, bila dataset publik sudah diadaptasi dan batas interpretasinya dicantumkan.

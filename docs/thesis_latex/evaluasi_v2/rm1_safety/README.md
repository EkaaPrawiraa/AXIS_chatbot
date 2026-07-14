# RM1 -- Keselamatan Percakapan

## Re-run LLM-as-judge (2026-07-14)

`llm_judge_results.json` merupakan hasil pengulangan terhadap 50 pesan: 42
kasus benchmark awal dan delapan tambahan formal atau bahasa campur. Dua model
Gemini menilai label risiko serta ragam bahasa secara buta; perbedaan
diselesaikan oleh konfigurasi adjudikasi terpisah. Sistem kemudian dijalankan
terhadap setiap pesan. Hasil agregat adalah TP=17, FN=7, FP=2, dan TN=24
(sensitivitas 0,708; spesifisitas 0,923; presisi 0,895; $F_2$ 0,739).

Kepatuhan respons setelah kasus tertangkap dinilai pada empat butir: pengakuan
tanpa menghakimi, batas non-klinis, rujukan yang sesuai, dan tidak menawarkan
CBT yang tidak sesuai krisis. Semua respons yang ditinjau memenuhi keempat
butir. Nilai ini tidak menutup kelemahan deteksi: tujuh kasus berisiko masih
tidak tertangkap dalam korpus tersebut.

Artefak `results.json` menyimpan benchmark awal yang lebih kecil dan
dipertahankan untuk histori. Bab IV memakai `llm_judge_results.json` sebagai
sumber angka akhir karena korpusnya sudah diberi label ragam bahasa dan dinilai
ulang dengan protokol penilai buta.

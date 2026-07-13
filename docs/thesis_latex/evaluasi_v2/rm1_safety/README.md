# RM1b - Benchmark Keselamatan Percakapan

Dijalankan nyata langsung terhadap fungsi guardrail produksi (`evaluate_input`, `evaluate_pregen`) menggunakan korpus adversarial eufemisme krisis yang sudah ada (19 kalimat positif berisiko tinggi, disamarkan tanpa kata kunci literal; 23 kalimat negatif keras, termasuk kalimat yang sengaja berbagi kata dengan frasa sinyal krisis tapi tidak bermakna krisis).

Perintah:
```
cd agentic && ../.venv/bin/python3 -c "..."  # lihat riwayat sesi untuk skrip persis
```

## Hasil nyata

| | Nilai |
|---|---|
| TP (positif tertangkap) | 14 / 19 |
| FN (positif terlewat) | 5 / 19 |
| FP (negatif salah tertangkap) | 1 / 23 |
| TN (negatif benar tidak tertangkap) | 22 / 23 |
| Sensitivitas | 0,737 |
| Spesifisitas | 0,957 |
| Presisi | 0,933 |
| F2 | 0,769 |

Catatan: korpus ini belum memisahkan label ragam bahasa (formal/informal/bahasa campur/eufemistik) secara eksplisit per kalimat - mayoritas kalimat informal/eufemistik, 3 kalimat berbahasa Inggris. Pemisahan per ragam bahasa yang rapi memerlukan penandaan ulang korpus, dicatat sebagai pekerjaan lanjutan terpisah.

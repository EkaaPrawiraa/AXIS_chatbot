# Migrasi Model Gemini

Tanggal: 14 Juli 2026

Model generasi AXIS dipindahkan dari `gemini-2.5-flash` ke
`gemini-3.5-flash`. Model untuk pekerjaan ringan, termasuk penulisan ulang
kueri dan sebagian penilai otomatis, dipindahkan dari
`gemini-2.5-flash-lite` ke `gemini-3.1-flash-lite`.

Pemetaan diterapkan pada lingkungan agentic lokal dan contoh, nilai bawaan
deployment, serta konfigurasi pipeline evaluasi. Konfigurasi TTS tidak diubah
karena menggunakan keluarga model suara yang terpisah. Artefak evaluasi lama
tetap menyimpan metadata model saat artefak tersebut dibuat; setiap run baru
akan mencatat konfigurasi pengganti ini.

# Dokumen Fitur AXIS — Indeks

Setiap file di folder ini adalah referensi kondisi kode **saat ini** untuk satu fitur — bukan log historis. Isinya langsung ditimpa (bukan ditambah sebagai entri baru bertanggal) setiap kali implementasi berubah, supaya dokumennya tetap ringkas dan tidak perlu membaca keputusan-keputusan lama untuk memahami kondisi sekarang. Bagian "Keterbatasan diketahui" di tiap dokumen menampung celah/batasan yang masih terbuka, ditulis sebagai fakta kondisi saat ini, bukan sebagai narasi "sebelum vs sesudah diperbaiki".

Dokumen ini adalah bahan mentah untuk dua kebutuhan:
1. Menulis atau merevisi BAB III/IV laporan TA (ingat: laporan TA tidak boleh menyebut nama file/kelas kodebase — sitasi file di dokumen ini hanya untuk kebutuhan internal, bukan untuk disalin langsung ke laporan).
2. Bahan diskusi kritis — kekurangan, potensi perbaikan, trade-off yang belum terselesaikan.

## Daftar Fitur

| # | Fitur | File |
|---|---|---|
| 1 | Alur Percakapan Inti (routing pipeline agentik) | [01-alur-percakapan-inti.md](01-alur-percakapan-inti.md) |
| 2 | Guardrail Berlapis & Eskalasi Krisis | [02-guardrail-berlapis.md](02-guardrail-berlapis.md) |
| 3 | Kebijakan Dialog CBT | [03-kebijakan-dialog-cbt.md](03-kebijakan-dialog-cbt.md) |
| 4 | Mood Checker & PHQ-9 | [04-mood-phq9.md](04-mood-phq9.md) |
| 5 | Memori Jangka Panjang (Knowledge Graph + pgvector) | [05-memori-jangka-panjang.md](05-memori-jangka-panjang.md) |
| 6 | Interaksi Suara & Confession Space | [06-suara-confession-space.md](06-suara-confession-space.md) |
| 7 | Pengayaan Linguistik (deteksi bahasa & code-mixing) | [07-pengayaan-linguistik.md](07-pengayaan-linguistik.md) |
| 8 | Autentikasi & Manajemen Akun | [08-autentikasi-akun.md](08-autentikasi-akun.md) |
| 9 | Evaluation Pipeline (studi kasus komparatif) | [09-evaluation-pipeline.md](09-evaluation-pipeline.md) |
| 10 | Katalog Prompt Sistem | [10-katalog-prompt.md](10-katalog-prompt.md) |
| 11 | Audit Graph Agentik per Pesan | [11-audit-graph-agentik.md](11-audit-graph-agentik.md) |
| 12 | Thinking Budget Response Generator Gemini | [12-response-generator-thinking.md](12-response-generator-thinking.md) |

## Catatan referensi silang

Kritik independen yang sudah dikumpulkan (lihat `docs/thesis_review/10-jul-26.md` dan `docs/thesis_review/evaluation`) sudah didistribusikan ke bagian "Catatan Berkembang" pada dokumen fitur yang relevan, bukan didokumentasikan ulang di tempat terpisah.

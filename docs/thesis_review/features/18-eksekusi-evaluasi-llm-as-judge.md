# Eksekusi Evaluasi Bab IV dengan LLM-as-Judge

Tanggal: 2026-07-14

## Perubahan pendukung

Pool `asyncpg` pgvector kini diperiksa sebelum dipakai ulang. Pool yang terikat
ke event loop yang telah tertutup dibuat ulang, sehingga pengujian asinkron tidak
lagi gagal secara intermiten. Fixture memori juga memakai UUID valid karena
kolom `user_id` pada pgvector bertipe UUID.

## Verifikasi

Suite komponen kritis dijalankan ulang dari lingkungan lokal dengan hasil:

```text
163 passed
```

Ruang lingkupnya mencakup asesmen/PHQ-9, `Confession Space`, kendali pengguna,
ekspansi graf, evolusi keyakinan, dan penulis knowledge graph.

## Artefak evaluasi

- RM1 keselamatan: `docs/thesis_latex/evaluasi_v2/rm1_safety/llm_judge_results.json`.
  Dua penilai buta dan adjudikasi menilai 50 pesan serta kepatuhan respons
  setelah deteksi.
- RM2 PHQ-9: `docs/thesis_latex/evaluasi_v2/rm2_phq9/llm_judge_extended_results.json`
  dan `llm_judge_extended_metrics.json`. Korpus berisi 40 jawaban bebas dan
  menguji pemetaan skor, klarifikasi, serta rute item kesembilan.
- RM2 kontrak produksi: `docs/thesis_latex/evaluasi_v2/rm2_phq9/contract_test_results.json`.
  Suite penawaran, pemicu onboarding, pengisian, klarifikasi, penskoran,
  umpan balik, dan rute graf dijalankan kembali dengan hasil 130 lulus dan 0 gagal.
- RM3 tetap memakai artefak `recall_probe_condition_A_hybrid.json`,
  `recall_probe_condition_B1_vector_only.json`, dan
  `recall_bootstrap_ci.json`. Metrik peringkat berjenjang belum ditambahkan
  karena keluaran probe lama tidak menyimpan urutan kandidat berlabel.

## Batas

Penilaian otomatis tidak menggantikan evaluasi pengguna nyata. Studi pengguna
tetap berada pada evaluasi lanjutan.

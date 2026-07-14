# Audit Netral Evaluasi Bab IV

Tanggal audit: 14 Juli 2026  
Ruang lingkup: artefak pada `docs/thesis_latex/evaluasi_v2/`, isi Bab IV pada
`docs/thesis_latex/chapters/bab4_evaluasi_v2.tex`, serta hasil kompilasi
`seminar_hasil_v2.tex`.

## Putusan

Pelaporan evaluasi dapat dipertahankan sebagai bukti purwarupa dan tidak
mengklaim validasi pengguna atau validitas klinis. Angka yang dicantumkan pada
Bab IV memiliki artefak JSON atau keluaran uji yang dapat ditelusuri.

## Pemeriksaan metode

- RM1 keselamatan memakai korpus 50 pesan berlabel, dua konfigurasi penilai
  buta, dan adjudikasi berinstruksi terpisah saat terjadi ketidaksepakatan.
  Sensitivitas 0,708 dan tujuh kasus luput tetap disebutkan; hasil ini tidak
  dapat dipakai sebagai klaim bahwa deteksi eufemisme sudah memadai secara
  umum.
- RM2 memisahkan kontrak deterministik (130 lulus), pemetaan 40 jawaban bebas,
  serta rute item kesembilan. Kesepakatan sempurna pada korpus kecil hanya
  membuktikan kesesuaian pada kasus yang dirancang; kesetaraan dengan PHQ-9
  mandiri tetap tepat ditempatkan pada pengujian pengguna nyata.
- RM3 membedakan tiga jenis bukti: 27 kontrak lifecycle deterministik, probe
  retrieval parafrase, dan satu probe reappraisal ujung-ke-ujung. Penilaian
  semantik 3/5 menunjukkan mekanisme lifecycle berjalan, tetapi kualitas
  ekstraksi semantik belum cukup kuat untuk klaim umum.
- Dua penilai tidak selalu berarti tiga sumber independen: adjudikasi yang
  memakai konfigurasi berinstruksi terpisah harus diposisikan sebagai prosedur
  penyelesaian ketidaksepakatan, bukan penilai independen ketiga. Bab IV kini
  menggunakan formulasi tersebut.

## Ketertelusuran angka

| Klaim Bab IV | Artefak sumber |
|---|---|
| RM1, 50 pesan dan metrik klasifikasi | `rm1_safety/llm_judge_results.json` |
| RM2, 40 jawaban bebas dan metrik pemetaan | `rm2_phq9/llm_judge_extended_metrics.json` |
| RM2, 130 kontrak | `rm2_phq9/contract_test_results.json` |
| RM3, kontrak lifecycle | `rm3_memori/lifecycle_contract_results.json` |
| RM3, kesesuaian reappraisal 3/5 | `rm3_memori/lifecycle_llm_judge_results.json` |
| Kesepakatan antarpenilai | `judge_agreement.json` |

## Batas yang Masih Ada

- Korpus RM1 dan RM2 masih kecil serta tidak mewakili penggunaan nyata.
- RM3 belum memiliki korpus emas berjenjang untuk P@5, MRR, nDCG@5,
  *grounded-answer rate*, *contradiction rate*, atau *false-personalization
  rate*. Metrik itu tidak boleh diisi atau disimpulkan dari artefak saat ini.
- Penilaian LLM tidak menggantikan evaluasi pengguna, kenyamanan pengguna, atau
  validitas klinis. Ketiganya tetap ditandai sebagai evaluasi lanjutan.

## Pemeriksaan Dokumen

`latexmk -g -pdf -interaction=nonstopmode -halt-on-error seminar_hasil_v2.tex`
selesai pada 14 Juli 2026 tanpa kesalahan kompilasi atau referensi tak
terdefinisi. Peringatan yang tersisa berupa pemenggalan baris pada bibliografi
dan lampiran, bukan kegagalan evaluasi.

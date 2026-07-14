# Evaluasi RM3: Lifecycle dan Keterlacakan Memori

Tanggal: 2026-07-14

## Artefak baru

- `docs/thesis_latex/evaluasi_v2/rm3_memori/lifecycle_contract_results.json`
  menyimpan hasil pengulangan kontrak produksi.
- `docs/thesis_latex/evaluasi_v2/rm3_memori/lifecycle_reappraisal_probe.json`
  menyimpan keluaran probe finalizer lintas sesi yang digunakan sebagai sumber
  pemeriksaan lifecycle.
- `docs/thesis_latex/evaluasi_v2/rm3_memori/lifecycle_llm_judge_results.json`
  menyimpan label dua penilai LLM atas kesesuaian semantik relasi lifecycle
  pada probe tersebut.

## Hasil

Kontrak deterministik memori inti lulus 47/47. Subset penulisan, lifecycle,
dan context builder lulus 27/27; kendali pengguna lulus 4/4; dan pengecualian
aktivitas sesi untuk `Confession Space` lulus 2/2.

Pada satu probe pemaknaan ulang ujung-ke-ujung, dua penilai LLM menilai 3 dari
5 relasi yang ditulis selaras secara semantik dengan cerita pengguna. Tiga dari
tiga Thought yang disupersede berstatus tidak aktif. Hasil ini dicatat sebagai
bukti kecil dan tidak digeneralisasi sebagai ketepatan pembaruan memori pada
populasi atau korpus besar.

## Batas

Belum tersedia korpus relevansi berjenjang untuk P@5, MRR, nDCG@5 dan belum
tersedia pasangan jawaban berlabel untuk groundedness, kontradiksi, atau
personalisasi tanpa dasar. Bab IV mempertahankan metrik tersebut sebagai belum
diukur.

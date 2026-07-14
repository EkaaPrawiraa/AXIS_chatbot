# RM3 - Evaluasi Memori Jangka Panjang

## Recall@5 (kueri parafrase satu hop)

Dijalankan nyata via `evaluasi_v2/scripts/retrieval_recall_probe.py`, 3 pengguna x 5 fakta domain per pengguna (15 probe total), dieksekusi dua kali dengan `RETRIEVAL_MODE` berbeda:

- Kondisi A (hibrid, `RETRIEVAL_MODE=full`): `recall_probe_condition_A_hybrid.json` -> 15/15 = 1.00
- Kondisi B1 (vektor saja, `RETRIEVAL_MODE=vector_only`): `recall_probe_condition_B1_vector_only.json` -> 15/15 = 1.00

Kedua kondisi sama pada probe ini karena setiap kueri hanya butuh satu fakta domain yang mirip secara semantik dengan kueri (parafrase satu hop) - jenis kueri ini bisa dijawab pencarian vektor saja tanpa penelusuran relasi graf.

## Kalibrasi retrieval pada LongMemEval_S

`longmemeval_retrieval_results.json` merekam kalibrasi tambahan dengan 12
kueri yang dipilih secara acak-terstratifikasi (dua kueri untuk setiap enam tipe
pertanyaan) dari LongMemEval_S — korpus resmi yang menyediakan puluhan sesi
beserta sesi pengalih dan `answer_session_ids`. Setiap ringkasan sesi ditulis
melalui penulis memori AXIS, lalu dicari dengan pemeringkatan pgvector produksi.
Pada sampel ini, P@5 = 0,367, Recall@5 = 0,972, MRR = 0,833, dan nDCG@5 =
0,855.

Kalibrasi ini menguji pengambilan bukti sesi pada korpus eksternal, bukan
ablasi hibrid terhadap vektor-saja. Adapter tidak mengekstraksi node atau
relasi AXIS dari LongMemEval, sehingga hasilnya tidak dapat dipakai untuk
menyimpulkan keunggulan *knowledge graph*, ketepatan ekstraksi, atau
personalisasi pada mahasiswa Indonesia.

## Kasus bertarget: kueri berbagi entitas graf, kesamaan leksikal nol

Untuk mengisolasi nilai tambah graf secara lebih langsung, dijalankan kasus bertarget: dua Experience milik user yang sama, berbagi satu node Trigger yang identik (dospem susah dihubungi), tapi deskripsinya sengaja tidak berbagi kata maupun makna semantik permukaan (satu soal dosen pembimbing, satu lagi soal liburan ke pantai). Pencarian vektor di-mock supaya hanya menemukan experience pertama (mensimulasikan kondisi vektor-saja yang gagal karena tidak ada kemiripan leksikal/semantik apa pun ke query).

Hasil: kondisi hibrid berhasil menyertakan experience kedua lewat satu hop tambahan pada node Trigger yang sama; kondisi vektor-saja tidak akan pernah menemukannya. Verifikasi unit test otomatis (live terhadap Neo4j asli, bukan mock database) ada di `agentic/tests/test_memory/test_graph_expansion.py`, dua test lulus:

- `test_sibling_experience_via_shared_trigger_surfaces_via_graph_expansion` - PASSED
- `test_no_expansion_when_no_shared_trigger_or_subject` (guard negatif, mencegah over-eager expansion) - PASSED

## Kontrak lifecycle dan penilaian semantik

`lifecycle_contract_results.json` merekam pengulangan kontrak produksi: 47
kontrak memori inti, 27 kontrak penulisan/lifecycle/konteks, 4 kontrak kendali
pengguna, dan 2 kontrak `Confession Space`; seluruhnya lulus. Kontrak ini
menguji transisi dan persistensi deterministik, bukan kualitas semantik
ekstraksi LLM.

`lifecycle_reappraisal_probe.json` adalah artefak probe end-to-end mentah yang
sudah tersedia (salinan dari `evaluation_pipeline/results/reappraisal_probe.json`):
dua sesi difinalisasi dan relasi lifecycle yang ditulis pada Neo4j dibaca
kembali. `lifecycle_llm_judge_results.json` merekam hasil penilaiannya: dua
konfigurasi penilai independen (`gemini-3.1-flash-lite` dan
`gemini-3.1-pro-preview`) menilai lima relasi yang teramati secara terpisah.
Konfigurasi penilai primer menilai satu dari lima relasi selaras secara
semantik dengan pemaknaan ulang yang tersurat; kesepakatan kedua konfigurasi
mencapai Cohen's kappa 0,55 (sedang, dibaca hati-hati karena n=5). Tiga dari
tiga Thought yang disupersede berstatus tidak aktif. Hasil kecil ini
menunjukkan bahwa transisi teknis tidak identik dengan ketepatan semantik
ekstraksi.

## Penulisan node dan update correctness (skenario-dan-hasil)

Tidak ada korpus publik berbahasa Indonesia yang menyediakan anotasi node dan
relasi *knowledge graph* memori pada domain mahasiswa. Sebagai gantinya,
`node_writing_and_update_results.json` (dihasilkan oleh
`evaluasi_v2/scripts/rm3_node_writing_and_update_eval.py`) merekam teknik
pengujian skenario-dan-hasil terhadap penulis memori (finalizer) produksi
yang sesungguhnya, bukan mock:

- **Penulisan node** (6 skenario pesan tunggal, node yang diharapkan
  diverifikasi manual per tipe dan kata kunci konten): tp=9, fp=4, fn=3,
  presisi=0,69, *recall*=0,75, *macro-F1*=0,72.
- **Update correctness** (4 skenario dua-sesi dengan aksi *lifecycle* acuan
  `reappraise`/`replace`): 3 dari 4 aksi sesuai acuan (0,75); satu kasus
  meleset karena ekstraktor menghasilkan `SUPERSEDES` alih-alih
  `REAPPRAISED_AS` yang diharapkan.

Hasil ini menggambarkan perilaku ekstraktor pada dua belas skenario yang
diuji secara langsung, bukan estimasi presisi/*recall*/*update correctness*
pada populasi percakapan mahasiswa yang lebih luas. Akurasi label Topik,
Peran Subjek, Pemicu, dan kategori domain mahasiswa secara terpisah, serta
`stale-memory rate`, tidak tercakup pada skenario ini.

Kalibrasi eksternal telah menyediakan P@5, MRR, dan nDCG@5 untuk retrieval
sesi. Sebaliknya, `grounded-answer rate`, `contradiction rate`, dan
`false-personalization rate` masih belum dihitung karena memerlukan pasangan
jawaban berlabel; metrik tersebut tidak dianggap lulus.

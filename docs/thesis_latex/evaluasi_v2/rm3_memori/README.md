# RM3 - Evaluasi Memori Jangka Panjang

## Recall@5 (kueri parafrase satu hop)

Dijalankan nyata via `evaluasi_v2/scripts/retrieval_recall_probe.py`, 3 pengguna x 5 fakta domain per pengguna (15 probe total), dieksekusi dua kali dengan `RETRIEVAL_MODE` berbeda:

- Kondisi A (hibrid, `RETRIEVAL_MODE=full`): `recall_probe_condition_A_hybrid.json` -> 15/15 = 1.00
- Kondisi B1 (vektor saja, `RETRIEVAL_MODE=vector_only`): `recall_probe_condition_B1_vector_only.json` -> 15/15 = 1.00

Kedua kondisi sama pada probe ini karena setiap kueri hanya butuh satu fakta domain yang mirip secara semantik dengan kueri (parafrase satu hop) - jenis kueri ini bisa dijawab pencarian vektor saja tanpa penelusuran relasi graf.

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

`lifecycle_reappraisal_probe.json` adalah artefak probe end-to-end yang sudah
tersedia: dua sesi difinalisasi dan relasi lifecycle yang ditulis pada Neo4j
dibaca kembali. Dua penilai LLM buta (`gpt-4o-mini` dan `gpt-4.1-mini`) menilai
lima relasi yang teramati. Tiga dari lima relasi dinilai selaras secara
semantik dengan pemaknaan ulang yang tersurat; tiga dari tiga Thought yang
disupersede berstatus tidak aktif. Hasil kecil ini menunjukkan bahwa transisi
teknis tidak identik dengan ketepatan semantik ekstraksi, sehingga tidak
digeneralisasi sebagai `update correctness` populasi.

Metrik P@5, MRR, nDCG@5, `grounded-answer rate`, `contradiction rate`, dan
`false-personalization rate` belum diisi karena belum tersedia korpus relevansi
berjenjang maupun pasangan jawaban berlabel. Bab IV menyatakannya secara
eksplisit, bukan menganggapnya lulus.

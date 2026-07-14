# Fitur 2: Guardrail Berlapis & Eskalasi Krisis

## Ringkasan
Empat lapis pemeriksaan keselamatan (*defense in depth*) yang menjaga AXIS tetap non-klinis dan menangani sinyal krisis: instruksi lingkup di system prompt, filter kata kunci/regex di input, deteksi semantik eufemisme pra-generasi plus peninjauan pasca-generasi, dan penandaan sensitivitas memori. *Test suite* di `agentic/tests/test_feature_bot/test_guardrail/` saat ini 80/80 lulus. Lapis 3 (deteksi eufemisme) sudah diuji lewat benchmark adversarial nyata, bukan cuma unit test kualitatif: 14/19 (74%) kalimat ide bunuh diri yang disamarkan (tanpa kata kunci literal apa pun) tertangkap, dengan 1/18 kalimat keluhan mahasiswa biasa yang keliru tertangkap sebagai krisis. Detail dan daftar kalimatnya ada di `agentic/tests/test_feature_bot/test_guardrail/test_layer3_adversarial_euphemism.py` dan Lampiran (Subbab benchmark adversarial).

## Lapis 1 — System prompt (identitas)
Bukan kode, melainkan instruksi tetap di awal setiap prompt (`prompts/system/axis_identity.yaml`, isi lengkap di Lampiran F laporan TA). Mendefinisikan batas non-klinis, larangan diagnosis/rekomendasi obat, dan protokol krisis di level instruksi model.

## Lapis 2 — Validasi input leksikal + regex
Implementasi: `agentic/agent/nodes/input_guardrail.py`. Fungsi `evaluate_input()` mengecek pesan pengguna berurutan terhadap:
1. `CRISIS_KEYWORDS_ID` / `CRISIS_KEYWORDS_EN` (dari `prompts/guardrails/input_validation.yaml`, dimuat dan di-*compile* jadi regex dengan word-boundary Unicode) → jika cocok, `decision="escalate_crisis"`.
2. `JAILBREAK_PATTERNS` → `decision="block"`, alasan `jailbreak_pattern`.
3. `OFF_SCOPE_PATTERNS` (permintaan deliverable seperti kode/PR/esai/jawaban ujian) → `decision="block"`, alasan `off_scope`. Untuk kasus ini, respons penolakan (`_OFF_SCOPE_REFUSAL_ID`/`_EN`) langsung di-set sebagai `final_response` dan **melewati LLM sama sekali**, satu-satunya jalur di seluruh graf yang tidak memanggil model bahasa untuk menyusun balasannya.

Lapis ini murni pencocokan literal by design. Paraphrase yang tidak memuat kata kunci di atas memang dibiarkan lolos ke Lapis 3.

## Lapis 3 — Deteksi semantik eufemisme pra-generasi + peninjauan pasca-generasi
Dua mekanisme berbeda dalam `crisis_guardrail.py` dan `output_guardrail.py`.

**Pra-generasi** (`evaluate_pregen()` di `crisis_guardrail.py`): mencocokkan pesan terhadap 22 `CRISIS_SIGNAL_PHRASES` (`prompts/guardrails/pre_generation.yaml`) pakai skor *containment* asimetris. `_containment()` menghitung proporsi kata penyusun frasa acuan yang ditemukan di pesan (`|phrase_tokens ∩ message_tokens| / |phrase_tokens|`), bukan kemiripan dua arah macam Jaccard/Dice. Ini disengaja: frasa acuan pendek (3-5 kata) tidak boleh kalah hanya karena kalimat percakapan nyata jauh lebih panjang (10-15 kata). Metode dua-arah yang lama pernah diuji dan gagal total, 0 dari 19 kalimat pada benchmark adversarial di bawah, karena penyebut skornya ikut membesar oleh panjang kalimat, bukan oleh kedekatan makna. Ambang saat ini `CRISIS_SEMANTIC_THRESHOLD=0.4` plus syarat minimal satu kata bermuatan makna (`CRISIS_MIN_CONTENT_OVERLAP=1`, dihitung setelah `_STOPWORDS` disaring) agar frasa pendek tidak cocok hanya karena kata fungsi kebetulan sama.

Ada tiga penyempurnaan tambahan pada mekanisme ini, semuanya lahir dari kasus *false positive* nyata yang ditemukan lewat pengujian end-to-end, bukan spekulasi:
- `_STOPWORDS` diperluas dengan "lain", "orang", "besok". Ketiganya generik kalau berdiri sendiri (mis. "contoh skripsi lain", "besok coba lagi") dan baru jadi diagnostik untuk frasa krisis tertentu kalau berpasangan dengan kata lain ("orang lain", "bangun ... besok"). Tiap penambahan disertai komentar inline yang merujuk kalimat pemicu false positive-nya.
- `_phrase_needs_negation_ada()` menangani frasa berpola "tidak/gak/ga ada" (mis. "tidak ada harapan lagi"). Token overlap saja tidak bisa membedakan "tidak ada harapan" dari "masih ada harapan" karena unigram "ada" identik di keduanya, jadi fungsi ini mewajibkan kata negasi (`_NEGATION_MARKERS`) benar-benar bersebelahan dengan "ada" di pesan (dicek via `_NEGATION_ADA_RE`), bukan sekadar hadir di mana pun dalam kalimat. Ini memperbaiki false positive pada "masih ada harapan sih... nggak yakin juga bakal kelar".
- `_WEAK_PHRASE_CONTENT_SIZE`/`_WEAK_PHRASE_THRESHOLD` menaikkan ambang menjadi 0,6 (dari 0,4) untuk frasa acuan yang setelah stopword-stripping cuma tersisa 1 kata bermuatan makna, misalnya "beban" pada "jadi beban buat orang lain" setelah "orang"/"lain" distopword. Kata tunggal seperti itu sering polisemis: "beban pikiran" beda makna dari "beban buat orang lain".

**Pasca-generasi**: `agentic/agent/nodes/output_guardrail.py` mengecek keluaran draf LLM terhadap `DIAGNOSTIC_PATTERNS` dan `CLINICAL_INSTRUCTION_PATTERNS` (`prompts/guardrails/post_generation.yaml`). Jika cocok, memicu pemanggilan ulang LLM (`GUARDRAIL_REWRITE` spec) dengan instruksi menulis ulang tanpa klaim diagnosis, maksimum `MAX_REWRITE_ATTEMPTS=2` percobaan sebelum jatuh ke `guardrails/safe_fallback.yaml`. Mekanisme ini tidak berubah dari versi sebelumnya.

### Filter konten Gemini dinonaktifkan sebagian
`build_llm()` di `agentic/config/llm_models.py`, cabang provider Gemini, menyetel `safety_settings` untuk kategori harassment/hate/sexual/dangerous-content ke `HarmBlockThreshold.BLOCK_NONE`. Ini berlaku untuk semua pemanggilan LLM yang dirutekan lewat Gemini, bukan cuma node krisis, karena disetel di titik konstruksi klien yang sama. Alasannya: filter konten bawaan Gemini pernah memblokir teks distres yang sepenuhnya wajar ("masih banyak yang blank, takut gak kelar-kelar") dengan `block_reason: PROHIBITED_CONTENT`, memaksa AXIS jatuh ke fallback generik di tengah percakapan. Menonaktifkan filter itu dianggap dapat diterima karena AXIS sudah punya pipeline guardrail sendiri (Lapis 1-4 di atas) yang berjalan independen dari penyedia LLM manapun. Filter Gemini bukan satu-satunya lapis pertahanan, jadi menonaktifkannya tidak meninggalkan sistem tanpa pengaman.

## Lapis 4 — Penandaan sensitivitas Knowledge Graph
Implementasi: `agentic/memory/access_control.py`, memakai `prompts/guardrails/kg_sensitivity.yaml`. Node memori diberi tier (`normal` / `sensitive` / `restricted`) yang membatasi apa yang boleh masuk ke `kg_context` prompt (lihat dokumen Fitur 5).

## Alur triase krisis
`agentic/agent/nodes/crisis_guardrail.py` juga berisi `crisis_triage_node` dan `route_after_crisis_triage`, yang membagi krisis menjadi:
- **Tier 1** (niat aktif eksplisit) → `crisis_escalation_node`, memakai templat deterministik (`prompts/guardrails/crisis_response.yaml`) — **tidak pernah lewat LLM**, agar responsnya 100% dapat diandalkan saat risiko tinggi.
- **Tier 2** (ideasi pasif) → `crisis_empathy_node`, respons empati yang dibangkitkan LLM (`prompts/guardrails/crisis_empathy.yaml`) diikuti sisipan sumber bantuan deterministik.

Keduanya berujung ke `post_guardrail_router`, lalu bisa lanjut ke suara (jika mode voice) atau langsung `session_end`. Sesi tetap dapat dilanjutkan setelah respons krisis, bukan diakhiri paksa, sesuai desain agar pengguna tidak merasa "diputus" sistem saat krisis.

## Audit trail
Semua keputusan guardrail (Lapis 2, 3, dan sinyal linguistik) dicatat lewat `GuardrailLogger`/`GuardrailEvent` (`agentic/agent/audit/guardrail_events.py`) dengan `layer`, `decision`, `severity`, `trigger_detail`, dan `latency_ms`. Skema audit trail dijelaskan di Lampiran B laporan TA.

## Keterbatasan diketahui
- Recall Lapis 3 masih 74% (14/19), bukan 100%. Lima kalimat adversarial yang tersisa berbagi terlalu sedikit kata bermuatan makna dengan frasa acuan mana pun untuk lolos gerbang presisi. Ini celah struktural pendekatan berbasis containment kata, bukan pemahaman makna sesungguhnya.
- Dua kata sempat dicoba sebagai stopword lalu sengaja dibatalkan karena merusak recall pada kasus krisis asli: "baik" (kalau distopword, memutus deteksi pada "...kayaknya lebih baik aku nggak usah lahir aja") dan "capek" (kalau distopword, memutus deteksi pada "...capek jalanin hidup...pengen nyerah aja sekalian"). Konsekuensinya, false positive yang melibatkan dua kata ini pada konteks jinak (mis. "pembimbingku baik banget, malah dia yang nyuruh aku istirahat") tetap ada dan diterima sebagai batasan, karena melewatkan sinyal krisis asli dinilai lebih berisiko daripada satu false positive tambahan.
- Frasa produksi lama `"aku ingin pergi selamanya"` juga rentan false positive serupa (mis. "aku pergi jauh buat KKN, wifi kosan bisa dimatiin dulu" cocok lewat "aku"+"pergi" saja). Belum diperbaiki karena mengubah atau menghapus frasa produksi berada di luar cakupan perbaikan mekanisme containment ini.
- Tokenizer yang dipakai murni literal, tanpa stemming atau lemmatisasi. `_TOKEN_RE` mencocokkan kata apa adanya, jadi variasi morfologis seperti "jalanin" vs "menjalani" tidak dianggap sama; deteksi bergantung pada kata dalam `CRISIS_SIGNAL_PHRASES` muncul persis dalam bentuk yang sama di pesan pengguna.
- Benchmark adversarial masih berskala kecil (19 kalimat positif, 23 kalimat negatif keras setelah penambahan kasus temuan lapangan) dan disusun manual oleh satu orang. Cukup untuk menunjukkan mekanisme containment bekerja lebih baik dari Dice/Jaccard, tapi belum representasi statistik dari seluruh ragam eufemisme bahasa Indonesia mahasiswa.
- `safety_settings` BLOCK_NONE berlaku global untuk seluruh pemanggilan LLM Gemini, bukan hanya node krisis. Kalau ada celah di guardrail internal (Lapis 1-4) sekaligus provider aktif adalah Gemini, tidak ada lagi filter konten bawaan penyedia sebagai jaring pengaman kedua untuk kategori harassment/hate/sexual/dangerous-content.

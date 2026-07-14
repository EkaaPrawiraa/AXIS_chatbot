# Fitur 1: Alur Percakapan Inti (Routing Pipeline Agentik)

## Ringkasan
Setiap giliran chat (teks maupun suara) diproses oleh satu graf keputusan (LangGraph `StateGraph`) yang didefinisikan di `agentic/agent/graph.py::build_graph()`. Graf ini adalah tulang punggung yang menghubungkan semua fitur lain (guardrail, CBT, PHQ-9, memori, suara) — dokumen fitur lain merujuk balik ke topologi ini. Graf terdiri dari 18 node dan 19 kemungkinan cabang keputusan; validasi lewat eksekusi graf sungguhan (bukan simulasi atau uji node terisolasi) mengonfirmasi 18/18 node dan 18/19 cabang tereksekusi. Satu cabang (eskalasi langsung dari PHQ-9 tanpa lewat triase krisis) tidak pernah bisa tereksekusi karena penanda krisis lain selalu menyala bersamaan dan diperiksa lebih dulu — dicatat sebagai temuan audit di BAB IV, bukan sebagai kegagalan fungsional.

## Topologi node dan urutan eksekusi
```
entry
  ├─ (ada audio_input?) → speech_to_text → input_guardrail_node
  └─ (tidak)             → input_guardrail_node

input_guardrail_node
  ├─ decision=escalate_crisis → crisis_triage
  ├─ decision=block, reason=off_scope → output_guardrail (skip LLM sama sekali)
  ├─ decision=block, reason lain (jailbreak) → response_generator (LLM susun penolakan aman)
  └─ selain itu → linguistic_enrichment → phq9_check → crisis_guardrail
                    ├─ safety_flag=crisis → crisis_triage
                    └─ selain itu → memory_retrieval → dialogue_policy
                                      ├─ phq9.phase=offer_pending → response_generator
                                      ├─ phq9.phase∈{offered,in_progress,awaiting_clar} → phq9_delivery
                                      │     ├─ declined_note && !response_draft → response_generator
                                      │     └─ selain itu → output_guardrail
                                      └─ selain itu → response_generator
                                                          → output_guardrail
                                                              ├─ safety_flag∈{crisis,escalate} atau phq9.route_to_crisis_after → crisis_triage
                                                              └─ selain itu → post_guardrail_router
                                                                                ├─ voice_state.output_modality∈{voice,both} → speech_adapter → text_to_speech → session_end
                                                                                └─ selain itu → session_end → END

crisis_triage → (route_after_crisis_triage) → crisis_escalation | crisis_empathy → post_guardrail_router → (sama seperti di atas)
```

Referensi implementasi: `agentic/agent/graph.py` fungsi `route_entry`, `route_after_input_guardrail`, `route_after_crisis_check`, `route_after_dialogue`, `route_after_phq9_delivery`, `route_after_output_guardrail`, `route_after_output_finalized`.

## Node inisialisasi giliran (`entry` / `_turn_init_node`)
Sebelum node lain berjalan, `_turn_init_node` (di `graph.py`) mereset field transien per giliran (`response_draft`, `final_response`, `safety_flag`, `crisis_tier`, `kg_context`, dst.), memuat konteks profil pengguna (`display_name`, `preferred_language`, `gender`) dan konteks mood (mood hari ini + tren 7 hari terakhir dari tabel `user_moods`) langsung dari Postgres, lalu — khusus giliran pertama sesi (`session_turn == 0`) — memastikan node `User` sudah ada di Neo4j (`ensure_user_node`).

## Node penyusun respons (`response_generator_node`)
Didefinisikan di `agentic/agent/nodes/response_generator.py`. Menyusun prompt akhir dengan menumpuk beberapa blok secara berurutan (lihat `_build_messages`):
1. Prompt dasar — `nodes/response_generator_v2` secara default, atau `nodes/response_generator_v3` kalau `AXIS_RESPONSE_PIPELINE_VERSION=v3` (lihat bagian "Eksperimen v3" di bawah untuk detail arsitekturnya; lihat Lampiran F laporan TA untuk isi lengkap kedua prompt).
2. Prompt identitas sistem (`system/axis_identity`).
3. Overlay teknik CBT jika ada (`_technique_overlay`, lihat dokumen Fitur 3).
4. Blok konteks profil pengguna (nama, bahasa, gender, mood) — `_profile_context_block`.
5. Blok konteks memori (`kg_context` dari node `memory_retrieval`, lihat dokumen Fitur 5), diikuti blok `[Understanding Synthesis]` kalau pipeline v3 aktif dan datanya tersedia.
6. Overlay PHQ-9 offer/konfirmasi bila relevan.
7. Riwayat 4 pasang giliran terakhir (`_format_history`).

Model dipanggil lewat provider aktif (`LLM_PROVIDER`), dengan `temperature=1.0` dan `max_tokens=6000` (lihat `config/llm_models.py::RESPONSE_GENERATOR`), mendukung tool-calling hingga beberapa iterasi untuk kasus yang memerlukan pemanggilan alat (misal ambil URL).

Fungsi `_recent_name_usage_note()` memeriksa dua giliran asisten terakhir secara deterministik dan menyuntikkan larangan penyebutan nama pengguna sebagai overlay dinamis per giliran (larangan keras kalau nama baru dipakai giliran sebelumnya, larangan lunak kalau dipakai dua giliran lalu) — pendekatan kode ini terbukti menekan frekuensi penyebutan nama secara terukur, sementara instruksi *prompt* saja tanpa penjagaan berbasis kode tidak cukup diandalkan untuk perhitungan lintas giliran. Pola serupa berhasil diterapkan untuk dua temuan lain dari pengujian giliran nyata: `_question_ending_note()` (mendeteksi 3 giliran beruntun yang semuanya diakhiri tanda tanya, dikecualikan untuk teknik CBT yang pertanyaan penutupnya memang mekanisme inti teknik itu — lihat dokumen Fitur 3) dan `_repetitive_opener_note()` (mendeteksi 3 giliran beruntun yang berbagi kata pembuka yang sama, secara word-agnostic — tidak di-hardcode ke kata tertentu seperti "jadi"/"oh" supaya berlaku untuk pola pembuka apa pun yang diulang model). Ketiganya lahir dari pola yang sama: instruksi *prompt* murni untuk menghitung/melacak pengulangan lintas giliran terbukti tidak cukup diandalkan lewat pengujian giliran nyata berulang, sehingga kontrolnya dipindah ke kode yang menghitung riwayat sungguhan, bukan meminta model menghitung sendiri.

## Node penutup sesi (`session_end_node`)
Mencatat aktivitas sesi (turn count, timestamp terakhir) ke `SessionActivityRepository` agar proses latar (session sweeper — lihat dokumen Fitur 5) dapat menentukan kapan sesi layak difinalisasi.

## Ketergantungan lintas fitur
- `input_guardrail_node`, `output_guardrail`, `crisis_*` → dokumen Fitur 2 (Guardrail).
- `dialogue_policy` → dokumen Fitur 3 (CBT).
- `phq9_check`, `phq9_delivery` → dokumen Fitur 4 (Mood & PHQ-9).
- `memory_retrieval` → dokumen Fitur 5 (Memori Jangka Panjang).
- `speech_to_text`, `speech_adapter`, `text_to_speech` → dokumen Fitur 6 (Suara).
- `linguistic_enrichment` → dokumen Fitur 7 (Pengayaan Linguistik).

---

## Eksperimen v3: reasoning terpisah (`understanding_synthesis`) dan kalibrasi domain (2026-07-14)

Perombakan total lapisan pemahaman-ke-respons, dipicu evaluasi mandiri bahwa retrieval memori sudah kaya (dokumen Fitur 5) dan kebijakan dialog CBT sudah berjalan (dokumen Fitur 3), tapi prompt `response_generator` memperlakukan memori sekadar bahan *callback* satu kalimat, bukan model pemahaman utuh tentang pengguna. Diaktifkan lewat env var `AXIS_RESPONSE_PIPELINE_VERSION` (`v2` default, `v3` untuk pipeline baru) — pada `v2`, node `understanding_synthesis` tidak dieksekusi sama sekali dan `response_generator` memuat `nodes/response_generator_v2` seperti biasa, sehingga perbandingan v2-vs-v3 adalah perbandingan pipeline utuh (termasuk biaya latensi node baru), bukan micro-swap satu prompt.

### Arsitektur dua tahap
- **`understanding_synthesis`** (node baru, `agentic/agent/nodes/understanding_synthesis.py`, hanya berjalan di jalur `v3`, diselipkan antara `memory_retrieval` dan `dialogue_policy`) — "analis batin": reasoning 8 tahap (current emotion → unmet need → active pattern/belief → grounding experience → possible explanations berbobot persentase → triggering pattern → unspoken undercurrent → response guidance) atas `kg_context`, memakai LLM murah (`UNDERSTANDING_SYNTHESIS` spec, `_DEFAULT_CHEAP`, temperature 0.3, 700 token) — lebih cepat/murah per panggilan, tapi tetap menambah satu hop LLM baru ke pipeline (trade-off latensi yang disadari sejak desain, bukan diabaikan). Outputnya (`state["user_understanding"]`) tidak pernah ditampilkan ke pengguna secara verbatim.
- **`response_generator` v3** (`nodes/response_generator_v3.yaml`) — "suara": menerjemahkan hasil `understanding_synthesis` jadi balasan hangat lewat blok `[Understanding Synthesis]`, dengan larangan tegas menyebut angka/persentase/istilah klinis ke pengguna.

Kontrak kepemilikan antar-prompt (wajib, supaya prompt final gabungan tidak pernah menyebut aturan yang sama dua kali dari sumber berbeda — prinsip "minimal set of information" dan "altitude" yang tepat dari panduan context-engineering Anthropic): identitas/larangan mutlak/protokol krisis tetap milik `axis_identity.yaml`; tone/register/frasa terlarang/batas nada-tanya-pembuka-repetitif-nama serta cara mengucapkan pemahaman jadi milik tunggal `response_generator` v3; pemahaman psikologis (mentalization, case formulation, trauma-informed lens) jadi milik tunggal `understanding_synthesis`; mekanisme spesifik tiap teknik CBT tetap di overlay masing-masing. Audit grep terhadap produksi sebelum perombakan mengonfirmasi tumpang tindih nyata (bukan cuma antisipasi) di lima tempat — larangan frasa "kondisi tersebut", penanganan label klinis, larangan pembuka "Wah", template validasi generik, deskripsi tone "teman kampus" — masing-masing dirapikan jadi satu sumber tunggal.

**Landasan akademik**: Mentalization (Bateman & Fonagy 2017), CBT Case Formulation (Beck — early experience → core belief → rule for living → trigger → automatic thought → emotion → behavior), Person-Centered Therapy (Rogers — unconditional positive regard, congruence, accurate empathy), Empathic Communication (Thwaites & Bennett-Levy), Trauma-Informed Care (prinsip SAMHSA — baca perilaku sebagai adaptasi, bukan patologi), Common Factors (Wampold — alliance, warmth, hope), Computational Empathy (Sharma et al. — sudah jadi dasar EPITOME di dokumen Fitur 9, bukan hal baru di sini).

### Kalibrasi domain mahasiswa Indonesia di lapisan pemahaman
Audit terhadap `kg_extractor.yaml` (aturan 8/8b, lihat dokumen Fitur 5) menemukan bug konsistensi nyata: skema JSON yang disisipkan ke LLM ekstraksi (`_KG_JSON_SCHEMA` di `finalizer_factory.py`) memuat enum generik yang tidak memuat label domain-kalibrasi sama sekali — bahkan contoh Rule 2 di prompt yang sama ("dospem" → role `thesis_advisor`) tidak muncul sebagai opsi valid di skema di baris berikutnya. Diperbaiki: enum `subjects.role`/`triggers.category`/`topics.category` disamakan dengan kosakata Rule 8/8b. `understanding_synthesis.yaml` diberi bagian "DOMAIN LENS" baru — sengaja tidak menulis ulang daftar label (kepemilikan kosakata tetap di `kg_extractor.yaml`, prinsip kontrak kepemilikan di atas), hanya menginstruksikan reasoning untuk mengenali label domain-kalibrasi sebagai sinyal nyata saat sudah ada di memori yang diambil.

### Penghapusan batas memory callback + guard anti-repetisi
`response_generator_v3.yaml` semula membatasi "maksimum 1 memory callback per respons" — batas ini dihapus, diganti instruksi memakai pemahaman sebanyak yang genuinely membantu, dengan repetisi dikontrol lewat riwayat jangka pendek. Mengikuti pola yang sudah terbukti di bagian atas dokumen ini (nama pengguna, nada-tanya, pembuka repetitif), kontrol repetisi ditaruh di kode, bukan cuma instruksi prompt: `_memory_repetition_note()` mendeteksi tumpang-tindih kata kunci antara `grounding_experience`/`active_pattern` giliran ini dengan 1-2 giliran asisten terakhir, menyuntikkan `STYLE GUARD` kalau terdeteksi memori/pola yang sama baru saja disebut.

### Verifikasi
25 test di `test_response_generator_name_guard.py` (termasuk 8 baru untuk guard memory-repetition), 8 test di `test_understanding_synthesis/`, regresi penuh 497/503 lulus (6 gagal terkonfirmasi pre-existing/lingkungan). Perbandingan real 4 arah (cold-start × rich-memory, v2 × v3) dijalankan lewat `evaluation_pipeline/simulate.py`, hasil di `evaluation_pipeline/results/{coldstart,richmemory}_{v2,v3}.md`.

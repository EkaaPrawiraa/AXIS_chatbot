# Fitur 6: Interaksi Suara & Confession Space

## Ringkasan

Confession Space bukan satu mekanisme tunggal, melainkan dua sumbu independen yang kebetulan dipicu bersamaan oleh satu halaman frontend: (1) `confession_mode: bool` (`agentic/agent/state.py`) — gerbang persistensi & PHQ-9, dan (2) `voice_state.output_modality`/`audio_input` — sumbu STT/TTS yang sama sekali tidak mengecek `confession_mode`. Keduanya bisa dipisah (mis. mode suara yang tetap disimpan, atau confession mode berbasis teks tanpa suara), tapi hari ini selalu dikirim bersamaan oleh halaman Confession Space.

## Alur `confession_mode`

- Frontend (`frontend_v2/app/confession-space/page.tsx`) membuat percakapan dengan `channel: 'confession'` lewat `chatAPI.createConversation`.
- Backend Go (`backend/services/chat/internal/usecase/chat_usecase.go`) menyimpan `Channel` pada `entity.Session`, lalu tiap `SendMessage` menghitung `isConfession := session.Channel == entity.ChannelConfession` dan mengirim `ConfessionMode: isConfession` ke service agentic.
  - Untuk sesi ini, pesan user/asisten **tidak pernah** lewat `messages.Append` — objek pesan dibentuk in-memory (`id.NewUUID()`, `time.Now()`) lalu langsung dikembalikan ke frontend tanpa masuk tabel `messages`.
  - `session.TurnCount` tetap di-increment dan `MarkSafetyEscalated` tetap bisa dipanggil — metadata operasional `chat_sessions`, bukan isi percakapan.
- `agentic/gateway/service/chat_graph.py` (`_request_to_state`) menyalin `request.confession_mode` ke `state["confession_mode"]`.

## Yang digerbang oleh `confession_mode` di agentic

- `agentic/agent/nodes/phq9_check.py`: kalau true, `phq9_state` langsung direset ke `empty_phq9_state()` — seluruh alur PHQ-9 di-skip turn itu.
- `agentic/agent/nodes/response_generator.py`: menambah overlay prompt `agentic/prompts/assessment/confession_mode.yaml` (larang singgung PHQ-9, izinkan balasan lebih panjang) dan menaikkan `max_tokens` ke `CONFESSION_MODE_MAX_TOKENS = 12000`.
- `agentic/agent/nodes/session_end.py`: upsert ke `SessionActivityRepository` (dibaca _session sweeper_, Fitur 5) di-skip lewat kondisi `not state.get("confession_mode")`.
- `agentic/agent/audit/graph_trace.py` (`persist_graph_audit`): audit graph per pesan (Fitur 11) juga di-skip penuh.
- Guardrail (`crisis_guardrail`, `input_guardrail`, `output_guardrail`) **tidak** mengecek `confession_mode` sama sekali — berjalan penuh tanpa pengecualian, sesuai catatan eksplisit di `confession_mode.yaml` ("privacy-safety trade-off, bukan safety-privacy trade-off").
- `memory_retrieval_node` juga tidak mengecek `confession_mode` — sesi ini tetap _membaca_ konteks KG/pgvector seperti biasa; yang digerbang hanya penulisan-balik ke memori jangka panjang.

## Sumbu suara (independen dari `confession_mode`)

`route_entry` (`agentic/agent/graph.py`) memilih `speech_to_text` kalau `voice_state.audio_input` terisi, dan `route_after_output_finalized` memilih `speech_adapter` → `text_to_speech` kalau `voice_state.output_modality` in (`voice`, `both`) — kedua percabangan ini murni soal ada/tidaknya audio, tidak peduli `confession_mode`.

- **STT** (`speech_to_text_node`): provider utama/fallback ditentukan `llm_provider()` (OpenAI ⟷ Gemini bertukar urutan); model OpenAI via `OPENAI_TRANSCRIBE_MODEL` (default `gpt-4o-mini-transcribe`), Gemini via `GEMINI_TRANSCRIBE_MODEL` (default `gemini-3.5-flash`).
- **Speech adapter** (`speech_adapter_node`): mode `v2_5_turbo` (default) vs `v3` (khusus teknik CBT `grounding`, `V3_TECHNIQUES`). Kalau `single_pass_voice=true` (hanya dikirim halaman Confession Space), langkah ini di-skip total: `response_generator_node` sendiri sudah menghasilkan teks gaya-lisan dalam satu pass (`speech_adapted_in_generator=True`), menghemat satu pemanggilan LLM per turn suara.
- **TTS** (`text_to_speech_node`): rantai fallback tiga provider lewat `run_tts_fallback_chain` — ElevenLabs → (Gemini atau OpenAI, urutan ikut `llm_provider()`) → provider ketiga, tiap kegagalan `increment("tts_failures_total", ...)`. Voice/model diambil dari profil pengguna (`voices.yaml` via `load_voice_catalog`) atau tier Gemini (`gemini_tts_tiers.py`: 3 tier model + pemetaan karakter suara ke gaya bicara/pacing).

## Permukaan suara di frontend

- **Confession Space** (`app/confession-space/page.tsx`): satu-satunya tempat yang memicu balasan TTS otomatis dalam turn yang sama (kirim audio → transkrip → balas → putar audio), lewat `output_modality: 'both'` + `single_pass_voice: true`.
- **Chat biasa** (`components/v2/chat/composer/ChatComposer.tsx`): tombol mic murni dikte suara-ke-teks (panggil `voiceAPI.transcribe`, isi ke composer) — tidak pernah kirim `output_modality` voice/both atau `confession_mode`; balasannya tetap teks biasa yang disimpan permanen seperti biasa.
- Koreksi atas framing "hanya Confession Space yang bersuara": chat biasa tetap punya satu jalur TTS lain, tombol putar per pesan asisten (`app/chat/page.tsx`, `playMessage`) yang memanggil endpoint terpisah `/voice/synthesize` (`ChatGraphService.synthesize_speech`) — menjalankan `speech_adapter_node` + `run_tts_fallback_chain` langsung, di luar graph utama, tanpa lewat `voice_state.output_modality`. Jadi lebih presisi: Confession Space satu-satunya tempat TTS terjadi otomatis sebagai bagian dari turn percakapan; chat biasa hanya punya TTS on-demand pasca-hoc atas teks yang sudah ada.

## Keterbatasan diketahui

- Latensi _end-to-end_ (`time-to-first-token`, `time-to-first-audio`, _round-trip_ total) tidak diagregasi/disimpan sebagai satu metrik. Yang benar-benar ada: `latency_ms` per-node (STT, speech adapter, TTS) dicatat dan disimpan ke tabel `guardrail_events` (`agentic/agent/audit/guardrail_events.py`), plus `_GraphTimingTracker` di `agentic/gateway/service/chat_graph.py` yang bisa menghitung durasi tiap node graph — tapi hanya aktif kalau env `AXIS_GRAPH_TIMING_LOG` diset, dan hasilnya cuma di-log (`uvicorn.error`), tidak disimpan sebagai data evaluasi.
- Kebocoran memori jangka panjang yang belum tertutup: `session_end_node` memanggil `_persist_thought_record()` **tanpa pernah mengecek `confession_mode`** — kalau teknik CBT Thought Record selesai (`cbt_state.thought_record.step == "done"`) dalam sesi Confession Space, catatannya tetap ditulis permanen ke Neo4j lewat `write_thought_record()`. Ini bertentangan dengan klaim "tidak ada yang disimpan" di `confession_mode.yaml`, karena tidak ada gate di `cbt/`/`dialogue_policy.py` yang menonaktifkan teknik Thought Record saat `confession_mode` aktif.
- Batas privasi ini hanya soal penyimpanan utama AXIS: audio/teks tetap diteruskan ke provider eksternal (OpenAI, Gemini, atau ElevenLabs) sesuai konfigurasi — bukan jaminan privasi pihak ketiga.
- _Speech emotion recognition_ sebagai sinyal tambahan masih ide, belum diimplementasikan.

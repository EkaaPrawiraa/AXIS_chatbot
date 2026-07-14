# Fitur 11: Audit Graph Agentik per Pesan

## Ringkasan
AXIS punya dua jalur audit yang terpisah dan saling melengkapi. Audit graph (dibahas di dokumen ini, tabel `agentic_graph_audits`) merekam seluruh perjalanan satu pesan lewat node LangGraph, node demi node. Audit guardrail (tabel `guardrail_events`, ditulis lewat `GuardrailEvent`/`PostgresGuardrailLogger` di `agentic/agent/audit/guardrail_events.py`) hanya merekam keputusan guardrail per layer (`input`/`pre_gen`/`post_gen`/`kg_access`) sebagai baris flat, independen dari graph trace. Satu baris `agentic_graph_audits` = satu pesan pengguna yang dipersist ke tabel `messages` dan dikirim ke layanan agentik.

## Skema tabel
Migrasi `backend/migrations/024_agentic_graph_audits.up.sql`: `id` bigserial, `message_id` UUID → FK `messages(id) ON DELETE CASCADE`, `user_id` UUID NOT NULL → FK `users(id) ON DELETE CASCADE`, `session_id` UUID → FK `chat_sessions(id) ON DELETE SET NULL`, `message_content` text, `graph` jsonb NOT NULL, `created_at` timestamptz. Index tersedia untuk `message_id`, `(user_id, created_at desc)`, `(session_id, created_at desc)`, dan GIN pada `graph`.

## Bentuk JSONB `graph`
Dibangun oleh `agentic/agent/audit/graph_trace.py`, bentuknya:
```
{
  "nodes": [{"node": ..., "event": "start"|"end"|"error", "at": iso8601, "state": {...}, "error"?: str}],
  "routes": [{"source": ..., "target": ..., "reason": ..., "condition": {...}, "at": iso8601}],
  "started_at": iso8601, "finished_at": iso8601,
  "final_state": {...}
}
```
Tiap node yang dibungkus `audited_node()` di `agentic/agent/graph.py` menghasilkan sepasang event `start`/`end` (atau `error` kalau exception), dan tiap event membawa snapshot state **penuh** lewat `graph_snapshot()` — bukan cuma di `final_state`. Artinya snapshot yang sama strukturnya terekam berulang kali per pesan (untuk pesan normal: ~22 kali node event + 1 kali `final_state`), bukan didiff antar event.

`graph_snapshot()` mengambil: `session_turn`, `resolved_language`, `safety_flag`, `crisis_tier`, `deferred_crisis_signal`, `input_guardrail{decision,reason,matched}`, `linguistic_signals`, `phq9{phase,tier,reason,active_item,last_judge_action,last_judge_rationale,item9_flagged,route_to_crisis_after,user_initiated,offer_armed}`, `cbt{active,directive,last_offered,declined_last_offer,decline_streak,thought_record_active,thought_record}`, `retrieval{kg_context_chars,has_kg_context,retrieval_context}`, `voice{output_modality,has_audio_input,has_transcript,tts_provider,tts_model,voice_error}`, dan `response{has_response_draft,has_final_response,response_draft_chars,final_response_chars}`.

## Alur implementasi & syarat FK
`ChatGraphService` (`agentic/gateway/service/chat_graph.py`) meng-set `state["current_message_id"]` dari `request.current_message_id` sebelum menjalankan graph, lalu memanggil `persist_graph_audit()` baik setelah `graph.ainvoke()` maupun setelah event `on_chain_end` di jalur streaming (`astream_events`). Backend chat Go selalu mengisi `CurrentMessageID` dengan ID baris `messages` yang sudah dipersist lebih dulu (`chat_usecase.go`), bukan ID sembarang.

`persist_graph_audit()` diam-diam no-op (tidak melempar exception ke pemanggil) kalau `current_message_id` atau `user_id` kosong, dan juga gagal diam-diam kalau `message_id` terisi tapi tidak merujuk baris `messages` yang benar-benar ada — *insert* akan kena pelanggaran FK dan itu cuma ditangkap sebagai `except Exception` generik lalu di-*log* sebagai *warning*, baris audit hilang total. Ini alasan `evaluation_pipeline/evaluate.py` dan `evaluation_pipeline/simulate.py` sama-sama harus insert baris `messages` asli lebih dulu (`_insert_message()` / `insert_message()`) sebelum memanggil graph; bug ini baru ditemukan dan diperbaiki di `simulate.py` pada 13 Juli 2026. Confession Space tetap dikecualikan lewat guard `state.get("confession_mode")` di baris pertama `persist_graph_audit()`.

## Verifikasi
Query langsung ke tabel produksi lewat container `companionshipchatbot-postgres-1` (13 Juli 2026) menunjukkan 305 baris tersimpan. Baris terbaru punya 22 event node, 6 event route, jalur `entry → input_guardrail_node → linguistic_enrichment → phq9_check → crisis_guardrail → memory_retrieval → dialogue_policy → response_generator → output_guardrail → post_guardrail_router → session_end`, dan `final_state` cocok persis dengan daftar *field* `graph_snapshot()` di atas (nilai nyata seperti `cbt.active="reframe"`, `phq9.phase="idle"`, `linguistic_signals.language="id"`). Kolom top-level `graph` juga cocok skema di atas: `nodes`, `routes`, `started_at`, `finished_at`, `final_state`. Mekanisme ini yang dipakai untuk menelusuri langsung keputusan routing CBT pada kasus nyata di tanggal yang sama.

## Keterbatasan diketahui
- Snapshot state penuh terekam ulang di tiap event node (bukan diff), jadi satu baris membawa duplikasi data yang sama berkali-kali; ukurannya sekarang masih kecil (~2,5 KB per pesan) tapi ikut membengkak kalau isi `kg_context` atau riwayat `cbt`/`phq9` membesar.
- Tidak ada *retention*/*pruning policy* untuk trafik produksi asli — baris dari sesi chat sungguhan tidak pernah dihapus. Ini beda dari `evaluation_pipeline/evaluate.py` yang membersihkan baris via `_cleanup_session()` khusus untuk sesi evaluasi; tabel ini akan terus bertambah tanpa batas untuk pemakaian normal.
- `evaluation_pipeline/simulate.py` insert baris `messages` demi lolos FK tapi tidak punya `_cleanup_session()` seperti `evaluate.py` — baris `messages` dan `agentic_graph_audits` hasil simulasi ikut menumpuk permanen kalau tidak dibersihkan manual.
- `PostgresGuardrailLogger._insert` (di `guardrail_events.py`) punya *retry* khusus kalau FK `session_id` gagal (insert ulang dengan `session_id=NULL` supaya baris tidak hilang); `persist_graph_audit()` tidak punya mekanisme serupa — begitu *insert* gagal karena FK apa pun, baris itu hilang total, cuma tersisa *warning* di log.
- Tidak ada dashboard atau endpoint API untuk menelusuri isi tabel ini; satu-satunya cara membacanya sekarang adalah query SQL langsung.
- *Delete* manual pada tabel ini harus selalu di-*scope* `WHERE session_id=...`, tidak pernah tanpa `WHERE`.

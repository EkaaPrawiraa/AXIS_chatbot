# Fitur 10: Katalog Prompt Sistem

## Ringkasan
Seluruh *system prompt* AXIS disimpan sebagai berkas YAML terpisah di `agentic/prompts/`, dimuat lewat `agentic/prompts/loader.py::load_prompt(ref)` / `load_prompt_bundle(ref)` (re-export via `agentic/prompts/__init__.py`). Loader mewajibkan key `name` dan `system`, meng-cache hasil parse per-ref di memori (`clear_cache()` untuk hot reload), dan **gagal cepat** — `PromptNotFoundError` kalau berkas tak ada, `PromptSchemaError` kalau YAML rusak atau key wajib hilang. Total 30 berkas prompt aktif di lima folder kategori (`system/`, `nodes/`, `cbt/`, `assessment/`, `guardrails/`), plus satu berkas `test_bot_main_prompt.yaml` di root yang bukan bagian skema ini (lihat bagian terpisah di bawah). Kedua *orphan* yang dicatat versi dokumen sebelumnya (`axis_identity_v2.yaml`, `response_generator.yaml` v1) sudah tidak ada lagi di direktori — sudah dibersihkan, bukan lagi masalah terbuka.

## Kategori `system/`
| Berkas | Peran & pasangan LLMSpec |
|---|---|
| `axis_identity.yaml` | Layer 1 — identitas, kapabilitas, larangan mutlak. Tidak dipanggil lewat LLMSpec sendiri: teksnya digabung langsung ke system message `RESPONSE_GENERATOR` lewat `_identity_prompt()` di `response_generator.py`. LLMSpec `SYSTEM_AXIS_IDENTITY` (model kuat, temp 1) ada di registry tapi tidak pernah dipanggil `build_llm()` di kode produksi manapun — vestigial. |

## Kategori `nodes/`
| Berkas | Peran & pasangan LLMSpec |
|---|---|
| `response_generator_v2.yaml` | Node balasan utama. LLMSpec `RESPONSE_GENERATOR` (model strong-generation, default `gpt-5.4-nano`, temp 1, max_tokens 6000, streaming). |
| `kg_extractor.yaml` | Ekstraksi Experience/Emotion/Trigger/Thought/Behavior/Subject ke skema KG. LLMSpec `KG_EXTRACTOR` (default `o4-mini`, temp 1, max_tokens 10000, reasoning_effort=high). |
| `session_summarizer.yaml` | Ringkasan sesi untuk memori, dipanggil `SessionFinalizer`. LLMSpec `SESSION_SUMMARIZER` (model kuat `gpt-5.5`, temp 1, max_tokens 6000). |
| `retrieval_query_rewriter.yaml` | Opsional (`RETRIEVAL_QUERY_REWRITE_ENABLED`), menyusun ulang pesan jadi query mandiri-konteks. LLMSpec `RETRIEVAL_QUERY_REWRITER` (default `gpt-4o-mini`, temp 0.0, max_tokens 140, timeout 10s). |
| `speech_adapter.yaml` / `speech_adapter_v3.yaml` / `speech_adapter_gemini_tags.yaml` | Adaptasi teks-ke-ucapan (mode v2.5/v3, tag prosodik Gemini). LLMSpec masing-masing `SPEECH_ADAPTER`, `SPEECH_ADAPTER_V3`, `SPEECH_ADAPTER_GEMINI_TAGS` — semua model murah, temp 0.0. |

## Kategori `cbt/`
| Berkas | Peran & pasangan LLMSpec |
|---|---|
| `router_judge.yaml` | LLM judge pemilih teknik CBT (Fitur 3). LLMSpec `CBT_JUDGE` (model murah, temp 0.0, max_tokens 200) — satu-satunya prompt di folder ini yang benar-benar jadi panggilan LLM terpisah (`agent/cbt/judge.py`). |
| `validate.yaml` | Fallback empatik saat tak ada teknik lain yang cocok. **Diedit hari ini**: instruksi menutup dengan satu pertanyaan terbuka dilunakkan — sekarang eksplisit bilang kalau ada *style guard* lain di prompt (larangan mengakhiri semua giliran terakhir dengan tanda tanya) mengharuskan bentuk lain, guard itu yang menang, karena "pekerjaan inti teknik ini adalah refleksi, bukan pertanyaannya." Tidak dipasangkan LLMSpec sendiri — dimuat lewat `PROMPT_REFS` di `agent/cbt/techniques.py` dan digabung sebagai overlay ke system message `RESPONSE_GENERATOR`. |
| `reframe.yaml`, `thought_record.yaml`, `behavior_activation.yaml`, `grounding.yaml`, `psychoeducation.yaml`, `self_compassion.yaml` | Lima teknik CBT lain. `reframe.yaml` tidak berubah — masih mewajibkan tepat satu pertanyaan Socratic penutup sebagai mekanisme inti tekniknya, tanpa pengecualian *style guard* seperti di `validate.yaml`. Sama seperti validate, dimuat lewat `PROMPT_REFS` dan digabung sebagai overlay ke `RESPONSE_GENERATOR`, bukan panggilan LLM sendiri. LLMSpec `CBT_REFRAME` dan `CBT_GROUNDING` ada di registry tapi sama-sama tidak pernah dipanggil `build_llm()` di produksi — vestigial. |

## Kategori `assessment/`
| Berkas | Peran & pasangan LLMSpec |
|---|---|
| `phq9_scorer.yaml` | Skoring jawaban. LLMSpec `PHQ9_SCORER` (murah, temp 0.0, max_tokens 100). |
| `phq9_conversation.yaml` | Administrasi item PHQ-9 percakapan. LLMSpec `PHQ9_CONVERSATION` (murah, temp 0.4, max_tokens 200). |
| `phq9_clarification_explainer.yaml` | Penjelas ulang saat jawaban ambigu. LLMSpec `PHQ9_CLARIFICATION_EXPLAINER` (murah, temp 0.4, max_tokens 250). |
| `phq9_feedback.yaml` | Umpan balik hasil ke pengguna. LLMSpec `PHQ9_FEEDBACK` (model kuat, temp 1, max_tokens 400). |
| `phq9_judge.yaml` | Judge klarifikasi/validitas jawaban. LLMSpec `PHQ9_JUDGE` (murah, temp 0.0, max_tokens 200). |
| `phq9_offer.yaml`, `confession_mode.yaml` | Penawaran PHQ-9 dan overlay Confession Space. Tidak ada LLMSpec sendiri — sama seperti prompt CBT, dimuat `load_prompt()` langsung lalu digabung sebagai overlay ke `RESPONSE_GENERATOR`. |

## Kategori `guardrails/`
| Berkas | Peran & pasangan LLMSpec |
|---|---|
| `crisis_empathy.yaml` | Balasan empatik tier-2 (ideasi pasif). LLMSpec `CRISIS_EMPATHY` (model kuat, temp 1, max_tokens 300) — satu-satunya teks krisis yang benar-benar dikirim ke LLM. |
| `post_generation.yaml` | Layer 3 rewrite loop. LLMSpec `GUARDRAIL_REWRITE` (model kuat, temp 1, max_tokens 600). |
| `input_validation.yaml`, `pre_generation.yaml`, `kg_sensitivity.yaml`, `crisis_response.yaml`, `safe_fallback.yaml` | **Bukan system prompt LLM** — menumpang skema loader yang sama (butuh key `name`+`system`) tapi isinya konfigurasi deterministik: daftar keyword/regex krisis (`input_validation`, juga dibaca gateway Go via parser bersama), parameter deteksi semantik & threshold (`pre_generation`), kebijakan tier sensitivitas KG untuk `context_builder` (`kg_sensitivity`), atau teks template statis yang dirender tanpa panggilan LLM sama sekali (`crisis_response` tier-1, `safe_fallback`). |

## Di luar skema loader
`test_bot_main_prompt.yaml` di root `agentic/prompts/` pakai key `system_prompt:`/`summary_system_prompt:`, bukan `name:`/`system:` yang diwajibkan `loader.py` — kalau dipaksa lewat `load_prompt()` akan gagal dengan `PromptSchemaError`. Ditelusuri sampai tuntas: tidak ada satu pun kode yang memuatnya. Harness manual (`agentic/tests/test_bot/test_bot_main.py`) punya konstanta `SYSTEM_PROMPT` sendiri yang di-hardcode terpisah dan isinya mirip tapi independen dari berkas ini — jadi berkas YAML ini murni salinan mati, bukan sumber yang benar-benar dipakai.

## Keterbatasan diketahui
- Loader (`loader.py`) sendiri sudah gagal cepat (`PromptNotFoundError`/`PromptSchemaError`), tapi beberapa pemanggil membungkusnya dengan `except Exception: return ""` (`response_generator.py::_base_prompt`, `_identity_prompt`) — silent-fail terjadi di titik pemanggilan, bukan di modul prompts itu sendiri seperti sempat dicatat sebelumnya.
- Tiga LLMSpec (`SYSTEM_AXIS_IDENTITY`, `CBT_REFRAME`, `CBT_GROUNDING`) lengkap dengan model/temperature/max_tokens di registry tapi tidak pernah dipanggil `build_llm()` di kode produksi — konfigurasinya vestigial, meski teks prompt terkait tetap terpakai lewat jalur overlay ke `RESPONSE_GENERATOR`.
- `test_bot_main_prompt.yaml` adalah dead weight terkonfirmasi (lihat bagian di atas), belum dihapus.
- Tidak ada test regresi yang memuat (`load_prompt`) setiap ref yang dipanggil kode produksi, sehingga perubahan path/nama berkas di masa depan bisa diam-diam jatuh ke fallback `""` di pemanggil yang membungkus exception, alih-alih gagal cepat sampai ke permukaan.

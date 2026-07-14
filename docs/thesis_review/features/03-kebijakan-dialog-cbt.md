# Fitur 3: Kebijakan Dialog CBT

## Ringkasan
Node `dialogue_policy` (`agentic/agent/nodes/dialogue_policy.py`) memutuskan teknik CBT apa (jika ada) yang ditumpuk sebagai overlay di atas prompt respons dasar (lihat dokumen Fitur 1). Tujuh teknik yang tersedia: `validate`, `reframe`, `thought_record`, `behavior_activation`, `grounding`, `psychoeducation`, `self_compassion` (enum `CBTTechnique`, `agentic/agent/cbt/techniques.py`).

## Dua jalur keputusan
1. **Jalur deterministik** (`agentic/agent/cbt/router.py::route()`) — pencocokan sinyal berbasis aturan (kata kunci, regex, deteksi distorsi kognitif). **Tidak pernah bisa menghasilkan `grounding`** — teknik ini hanya bisa dipilih lewat jalur judge, karena regulasi afek akut sengaja diprioritaskan di atas penantangan distorsi kognitif (Linehan, 1993, DBT).
2. **Jalur judge LLM** (`route_with_llm()`) — memanggil `judge_technique()` (`agentic/agent/cbt/judge.py`), yang mengirim pesan pengguna + riwayat + konteks KG + status opt-out ke LLM (`CBT_JUDGE` spec) dan mem-parse keluaran JSON (`technique`, `confidence`, `distortion`, `rationale`).

`route_with_llm()` dipanggil kalau `judge_llm` disediakan (produksi selalu menyediakannya); kalau judge gagal/timeout/tidak tersedia, sistem jatuh kembali ke `route()`.

## Rantai prioritas aturan (berlaku di kedua jalur, sebelum judge dipanggil)
`route()` dan `route_with_llm()` sama-sama mengevaluasi urutan tetap ini lebih dulu:
1. `_rule_safety_check` — gerbang keselamatan.
2. `_rule_grounding_followup_check` — susulan setelah grounding.
3. `_rule_stalled_validation_followup_check` — eskalasi validasi mandek (lihat bawah).

Hanya kalau ketiganya mengembalikan `None`, `route_with_llm()` baru mengecek gerbang giliran minimum lalu memanggil judge.

## Gerbang keselamatan (`_rule_safety_check`)
- `safety_flag∈{crisis,escalate}` → paksa `NONE`, dan reset `thought_record_active`/`thought_record` di `cbt_state` agar latihan reflektif yang sedang berjalan tidak diam-diam berlanjut begitu krisis mereda.
- `phq9_state.phase` sedang aktif → paksa `NONE` (tidak mencampur CBT dengan skrining).
- `thought_record_active=True` → langsung lanjutkan `THOUGHT_RECORD` (resume sub-state machine).

## Gerbang giliran minimum & ambang keyakinan
- `CBT_MIN_TURN_BEFORE_OFFER = 3` — teknik hasil jalur judge (termasuk `grounding`) tidak bisa menyala sebelum `session_turn` pengguna melewati giliran ke-3; di bawah itu, `route_with_llm` otomatis jatuh ke `route()` deterministik tanpa memanggil judge. Gerbang ini tidak berlaku untuk tiga aturan prioritas di atas — ketiganya bisa menyala di giliran berapa pun.
- `JUDGE_CONFIDENCE_THRESHOLD = 0.6` — ambang umum untuk menerima keputusan judge.
- `GROUNDING_CONFIDENCE_THRESHOLD = 0.7` — ambang khusus lebih ketat untuk `grounding`, karena bobot intervensinya lebih besar (memutus alur dengan latihan sensorik).

## Gerbang emosi pada distorsi kognitif segar
Di `route()`, cabang distorsi kognitif otomatis (`s.distortion is not None`) hanya berjalan kalau `s.has_emotional_content=True` atau distorsi berasal dari konteks lanjutan (`distortion_from_context=True`, yaitu giliran lanjutan dari teknik yang sudah berjalan). Permintaan eksplisit pengguna ("bantu reframe dong") tetap diproses tanpa gerbang ini. Detektor distorsi sendiri (`agentic/agent/cbt/distortions.py`) memakai pencocokan word-boundary regex, bukan substring mentah.

## Penekanan penolakan berturut (`decline_streak`)
`dialogue_policy_node` melacak `cbt_state["decline_streak"]`. Kalau nilainya ≥ `DECLINE_STREAK_SUPPRESS_THRESHOLD=2` dan keputusan hasil routing bukan `NONE`/`VALIDATE`, keputusan dipaksa turun ke `VALIDATE` dengan alasan `decline_streak_suppressed`. Streak hanya di-reset pada giliran yang benar-benar "sepi" secara alami (bukan hasil penekanan itu sendiri), bukan setiap kali teknik berbeda ditawarkan.

## Susulan setelah *grounding* (`_rule_grounding_followup_check`)
Kalau `cbt_state.last_directive.technique == grounding` dengan distorsi tercatat, dan giliran sekarang masih bermuatan emosi, sistem otomatis menawarkan `reframe` pada giliran tepat setelahnya (hanya sekali) — memastikan distorsi kognitif yang muncul bersamaan afek akut tetap ditantang balik, bukan dibiarkan lewat begitu saja setelah momen krisisnya reda. *Prompt judge* mencatat nama distorsi di *field* `distortion` bahkan ketika teknik yang dipilih adalah `grounding`, sehingga aturan susulan ini punya informasi yang dibutuhkan.

## Eskalasi validasi mandek (`_rule_stalled_validation_followup_check`)
Aturan kode deterministik, bukan instruksi di prompt judge — pendekatan prompt-only sempat dicoba dan dibatalkan karena model malah berhalusinasi soal state yang tidak ada. Kalau `cbt_state["turns_since_technique"]` (dilacak di `dialogue_policy_node`: naik setiap giliran yang berakhir `NONE`/`VALIDATE`, reset ke 0 begitu teknik lain menyala) sudah ≥ `STALLED_VALIDATION_TURNS_THRESHOLD=3`, direktif terakhir masih `VALIDATE`/`NONE`, dan sebuah distorsi kognitif masih bisa disimpulkan dari konteks (`_infer_context_distortion` — dari payload direktif terakhir atau dari bagian "unchallenged cognitive distortions" di `kg_context`), sistem mengeskalasi ke `reframe`. Aturan ini mundur (tidak jadi mengeskalasi) kalau pengguna jelas berganti topik (`_is_topic_shift`) atau baru saja menolak tawaran `reframe` (`declined_last` dengan `last_offered=="reframe"`). Diverifikasi lewat uji jalan 20-giliran nyata: menyala tepat saat `turns_since_technique>=3`, dan mundur dengan benar saat topik bergeser atau ada penolakan baru.

## Sub-state machine Thought Record
`agentic/agent/cbt/thought_record.py` — 5 langkah (`ThoughtRecordStep`): tangkap pikiran otomatis → beri label distorsi → bukti mendukung → bukti menentang → pikiran seimbang, dilacak lintas giliran via `ThoughtRecordSubState`, dapat menerima `hinted_distortion` dari sinyal KG.

## Guard penutup pertanyaan & pengecualian `reframe`/`thought_record`
`response_generator.py::_question_ending_note()` (di luar `router.py`, tapi berinteraksi langsung dengan pilihan teknik CBT) biasanya menekan penutup kalimat "?" setelah 3 giliran asisten berturut-turut berakhir tanda tanya, supaya tidak terasa seperti daftar periksa terapi. Sejak 2026-07-13 guard ini punya *frozenset* pengecualian `_QUESTION_MANDATORY_TECHNIQUES = {reframe, thought_record}`: kalau `state["cbt_node_active"]` salah satu dari keduanya, guard tidak dipasang sama sekali.

Alasannya adalah bug nyata yang ditemukan lewat uji jalan 20-giliran: router memilih `reframe` tepat pada giliran yang sama saat guard penutup-pertanyaan juga menyala, dan model membuang pertanyaan Socratic wajib di `reframe.yaml` ("ask ONE open Socratic question") demi patuh ke guard — diam-diam menggagalkan seluruh tujuan memilih `reframe` di giliran itu. Untuk kedua teknik ini pertanyaan penutup memang *mekanisme inti* teknik itu sendiri, bukan gaya penutup opsional, sehingga tidak boleh ditekan. `validate.yaml` diperbarui di hari yang sama untuk mengakui guard ini secara eksplisit: kalau guard menyala, validate ditutup dengan pernyataan hangat tanpa tanda tanya, karena inti teknik itu adalah refleksi, bukan pertanyaannya — jadi validate tetap kena guard seperti biasa.

Diuji di `agentic/tests/test_feature_bot/test_generate_response/test_response_generator_name_guard.py`: `test_question_guard_exempts_reframe`, `test_question_guard_exempts_thought_record` (guard tidak dipasang), `test_question_guard_still_fires_for_validate` (guard tetap dipasang seperti biasa). File yang sama juga menguji guard gaya lain di modul ini (`test_opener_guard_*` untuk pembuka kalimat yang berulang, `test_*name_guard*` untuk pengulangan nama pengguna) yang tidak spesifik-CBT sehingga tidak dibahas lebih jauh di sini.

## Keterbatasan diketahui
- Setelah `grounding` diterima, penyampaiannya cenderung berurutan seperti daftar periksa (giliran demi giliran: visual → taktil → auditori) dengan pembuka kalimat yang berulang — sedikit bertegangan dengan tujuan desain "jangan terasa seperti skrip terapi".
- Gerbang giliran minimum berlaku seragam untuk semua tingkat keyakinan, sehingga berpotensi menunda `grounding` pada kasus distres akut yang genuin muncul sangat dini (sebelum giliran ke-3) — tapi tidak berlaku untuk tiga aturan prioritas di atas (termasuk eskalasi validasi mandek), yang bisa menyala di giliran berapa pun.
- Potensi jalan buntu antara eskalasi validasi mandek dan penekanan penolakan berturut: kalau `decline_streak` sudah ≥ 2 tepat saat `_rule_stalled_validation_followup_check` mengusulkan `reframe`, `dialogue_policy_node` menekannya balik ke `VALIDATE` beralasan `decline_streak_suppressed` — dan karena alasan itu sengaja tidak me-reset `decline_streak`, giliran berikutnya `turns_since_technique` tetap ≥ 3 sehingga aturan yang sama mencoba lagi, lalu tertekan lagi. Siklus ini baru putus kalau topik bergeser atau muncul giliran "sepi" alami (bukan hasil penekanan) yang me-reset `decline_streak` ke 0. Belum diuji lewat skenario penolakan berulang plus distorsi yang menetap.
- Pengecualian guard penutup-pertanyaan untuk `thought_record` berlaku sepanjang sub-state machine-nya berjalan (bisa sampai 5 giliran berturut), bukan cuma satu giliran seperti kasus `reframe`. Kalau satu sesi thought record berjalan penuh, guard anti-"terasa skrip" itu absen sepanjang seluruh alurnya — risiko yang sama seperti keterbatasan `grounding` di atas berpotensi muncul lagi di sini, meski belum ada bukti dari uji jalan bahwa ini sudah benar-benar terjadi.

# Thinking Budget Response Generator Gemini

## Kondisi implementasi saat ini

Node `response_generator` memakai profil `RESPONSE_GENERATOR` (`agentic/config/llm_models.py`). Saat provider LLM disetel ke Gemini (`LLM_PROVIDER=gemini`), `build_llm()` mengecek `spec.name == "response_generator"` dan menambahkan kwarg `thinking_budget`/`include_thoughts` sebelum membentuk `ChatGoogleGenerativeAI`. Keduanya adalah field asli pada `ChatGoogleGenerativeAI` (paket `langchain-google-genai`, terverifikasi di `chat_models.py` versi terpasang) yang dipetakan ke `thinking_config` pada request generation config asli Gemini — mekanisme alokasi token *reasoning* internal sebelum model menyusun jawaban yang terlihat pengguna.

Gating ini berbasis nama profil, bukan nama model. Jika `preferred_response_model` (dari state percakapan) mengganti model response_generator ke varian Gemini lain — termasuk baris Gemini 3.x yang kini ada di `SUPPORTED_RESPONSE_MODELS` (`gemini-3.1-pro`, `gemini-3-flash`, `gemini-3.1-flash-lite`) — kwarg thinking tetap terpasang karena `dataclasses.replace()` mempertahankan `spec.name`. Default resolusi model tanpa override tetap `gemini-2.5-flash` (`GEMINI_MODEL_STRONG_GENERATION`). Belum ada bukti di kodebase/test bahwa varian Gemini 3.x menginterpretasikan `thinking_budget` dengan cara yang identik dengan 2.5; itu murni perilaku sisi provider.

Parameter ini berbeda dari `reasoning_effort` pada `LLMSpec` (dipakai mis. `KG_EXTRACTOR`) — itu knob milik OpenAI (`ChatOpenAI`), tidak dikirim ke Gemini dan tidak dipakai oleh `response_generator`.

Konfigurasi yang tersedia:

- `GEMINI_RESPONSE_GENERATOR_THINKING_BUDGET`
  - Default: `1024`
  - Jika `0`, kwarg `thinking_budget` sama sekali tidak dikirim ke constructor (bukan dikirim sebagai `0`), sehingga AXIS berhenti meminta alokasi token tertentu.
- `GEMINI_RESPONSE_GENERATOR_INCLUDE_THOUGHTS`
  - Default: `false`
  - Tetap disarankan `false`, karena aplikasi hanya perlu meminta proses thinking internal model, bukan menyimpan atau menampilkan isi reasoning internal. Kwarg ini selalu dikirim ke constructor (tidak bersyarat seperti `thinking_budget`).
- `AXIS_LOG_LLM_THINKING`
  - Default: `0`
  - Jika diaktifkan (`1/true/yes/on`), log agentic mencatat bahwa thinking diminta dan menampilkan ringkasan metadata usage/token yang aman. Log ini tidak menampilkan isi thought.

## Bukti audit yang dicatat

Pada event `response_generated`, metadata guardrail/audit menambahkan:

- provider LLM,
- model yang terselesaikan untuk `response_generator`,
- konfigurasi thinking request (`thinking_budget`, `include_thoughts`).

Metadata ini cukup untuk membuktikan bahwa request AXIS meminta thinking kepada Gemini tanpa membocorkan isi proses berpikir model.

## Sanitasi respons

Node `response_generator` juga melakukan sanitasi defensif pada keluaran model. Jika proses audit lokal sementara mengaktifkan `GEMINI_RESPONSE_GENERATOR_INCLUDE_THOUGHTS=true`, Gemini dapat mengembalikan `content` sebagai daftar blok yang mencampur blok `thinking` dan teks jawaban akhir. AXIS hanya mengambil blok teks yang terlihat untuk pengguna dan membuang blok `thinking` sebelum mengisi `response_draft`.

Dengan demikian, konfigurasi produksi tetap:

- meminta thinking melalui `thinking_budget`,
- tidak meminta isi thought melalui `include_thoughts=false`,
- tetap aman bila environment audit sementara tidak sengaja aktif karena blok `thinking` tidak disalin ke respons pengguna.

## Keterbatasan diketahui

- Tidak semua respons Gemini mengembalikan metadata token thinking yang terpisah melalui LangChain. Karena itu, bukti utama yang stabil adalah parameter request dan metadata audit, sedangkan usage token tambahan bergantung pada respons provider.
- Isi internal thinking tidak disimpan dan tidak ditampilkan. Ini sengaja dilakukan untuk menjaga batas keamanan dan menghindari kebocoran chain-of-thought.
- Menyetel `GEMINI_RESPONSE_GENERATOR_THINKING_BUDGET=0` tidak terbukti membuat Gemini benar-benar berhenti melakukan reasoning internal. Karena `include_thoughts` tetap dikirim (default `false`, bukan `None`), `thinking_config` pada request tetap terbentuk (berisi `include_thoughts` saja, tanpa `thinking_budget`) — bukan dihilangkan total. Yang bisa dipastikan dari kode: AXIS berhenti meminta angka budget eksplisit; apakah itu membuat provider jatuh ke thinking dinamis/default atau benar-benar nol belum diverifikasi lewat pengamatan response aktual, hanya lewat unit test yang mengecek kwarg constructor.

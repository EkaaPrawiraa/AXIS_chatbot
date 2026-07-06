<div align="center">
  <h1>AXIS Companion</h1>
  <p><strong>Companionship chatbot architecture with long-term memory for reflective student life.</strong></p>
  <p>
    Final project product by <strong>Mohammad Nugraha Eka Prawira</strong><br />
    Informatics Engineering, Institut Teknologi Bandung (ITB), Class of 2022
  </p>
  <p>
    <a href="#english">English</a> ·
    <a href="#bahasa-indonesia">Bahasa Indonesia</a> ·
    <a href="#installation-and-run">Run Guide</a>
  </p>
</div>

<hr />

<details open>
<summary id="english"><strong>English</strong></summary>

<h2>1. Project Name</h2>

<p><strong>AXIS Companion</strong> is a companionship chatbot application designed to support reflective conversations, emotional check-ins, personal memory exploration, and mental health adjacent self-awareness for students.</p>

<h2>2. Project Description</h2>

<p>AXIS Companion is built as a final project product by <strong>Mohammad Nugraha Eka Prawira (me)</strong>, Informatics Engineering, Institut Teknologi Bandung (ITB), Class of 2022. The product explores how a conversational system can provide a warm, structured, and safe interaction space for students who need a private place to speak, reflect, and understand recurring emotional patterns.</p>

<p>The application combines a modern web interface, a Go backend gateway, and an agentic Python service. It supports text chat, voice interaction, memory extraction, knowledge graph visualization, PHQ-9 guided screening flow, CBT-style conversation support, crisis guardrails, and hotline visibility.</p>

<h2>3. Problem Being Solved</h2>

<p>Many students experience stress, loneliness, academic pressure, and emotional overload, but they do not always have a low-friction place to process what they feel. Traditional journaling can feel lonely, while clinical tools can feel formal or intimidating. AXIS focuses on a middle space: a companion interface that is calm, conversational, and structured enough to help users reflect safely.</p>

<p>The project addresses several product and technical problems:</p>

<ul>
  <li>Creating a companion support experience with natural voice interaction in Indonesian, English, or mixed language use.</li>
  <li>Preserving conversation context without forcing users to repeat their background every session.</li>
  <li>Making emotional memory visible through a personal knowledge graph.</li>
  <li>Providing guardrails and hotline escalation when self-harm or crisis signals appear.</li>
  <li>Keeping the system modular so the frontend, backend services, and agentic workflow can evolve independently.</li>
</ul>

<h2>4. Main Features</h2>

<table>
  <tr>
    <th>Feature</th>
    <th>What It Does</th>
  </tr>
  <tr>
    <td><strong>Dashboard</strong></td>
    <td>Introduces the product, purpose, important notes, and final project context in a clean product surface.</td>
  </tr>
  <tr>
    <td><strong>Chat</strong></td>
    <td>Supports Markdown responses, compact message layout, crisis hotline cards, voice recording, and editable speech transcripts.</td>
  </tr>
  <tr>
    <td><strong>Voice Room</strong></td>
    <td>Provides a focused safe-space interface with microphone feedback, streaming transcript, spoken AI response, and delayed subtitle clearing.</td>
  </tr>
  <tr>
    <td><strong>Memory Library</strong></td>
    <td>Shows extracted personal memories and allows detail review through simple overlays.</td>
  </tr>
  <tr>
    <td><strong>Knowledge Graph</strong></td>
    <td>Visualizes memory nodes and relations with warm, distinct colors and privacy-conscious detail views.</td>
  </tr>
  <tr>
    <td><strong>PHQ-9 Flow</strong></td>
    <td>Guides users through mood screening questions while preserving score state and safety handling.</td>
  </tr>
  <tr>
    <td><strong>CBT-style Support</strong></td>
    <td>Routes conversations into supportive moves such as validation, psychoeducation, self-compassion, and grounding.</td>
  </tr>
  <tr>
    <td><strong>Crisis Guardrails</strong></td>
    <td>Detects high-risk messages, applies deterministic escalation behavior, and surfaces hotline resources.</td>
  </tr>
  <tr>
    <td><strong>Session Finalizer</strong></td>
    <td>Summarizes idle or long conversations into memory, checkpoints long sessions, and recovers retryable failures.</td>
  </tr>
</table>

<h2>5. Screenshots</h2>

<p>The repository currently provides screenshot slots below. Add real captures into <code>docs/screenshots/</code> using the listed filenames when preparing a report, demo deck, or final documentation package.</p>

<table>
  <tr>
    <th>Page or Feature</th>
    <th>Suggested File</th>
    <th>Capture Notes</th>
  </tr>
  <tr>
    <td>Dashboard</td>
    <td><code>docs/screenshots/dashboard.png</code></td>
    <td>Show the app explanation, important notes, and final project card.</td>
  </tr>
  <tr>
    <td>Chat</td>
    <td><code>docs/screenshots/chat.png</code></td>
    <td>Show a normal conversation with Markdown response and bottom typing box.</td>
  </tr>
  <tr>
    <td>Voice Room</td>
    <td><code>docs/screenshots/voice-room.png</code></td>
    <td>Show the safe-space screen, mic feedback, and transcript subtitle.</td>
  </tr>
  <tr>
    <td>Memory Library</td>
    <td><code>docs/screenshots/memories.png</code></td>
    <td>Show the simple memory list and overlay detail behavior.</td>
  </tr>
  <tr>
    <td>Knowledge Graph</td>
    <td><code>docs/screenshots/knowledge-graph.png</code></td>
    <td>Show colored nodes, relations, and the detail dialog.</td>
  </tr>
  <tr>
    <td>Hotlines</td>
    <td><code>docs/screenshots/hotlines.png</code></td>
    <td>Show crisis resource presentation and contact cards.</td>
  </tr>
  <tr>
    <td>Settings and Profile</td>
    <td><code>docs/screenshots/settings-profile.png</code></td>
    <td>Show language, voice preference, and account controls.</td>
  </tr>
</table>

<h2>6. Tech Stack and Rationale</h2>

<table>
  <tr>
    <th>Layer</th>
    <th>Technology</th>
    <th>Reason</th>
  </tr>
  <tr>
    <td>Frontend</td>
    <td>Next.js 16, React 19, TypeScript, Tailwind CSS v4</td>
    <td>Provides a typed, responsive, component-driven interface with fast iteration for product UI.</td>
  </tr>
  <tr>
    <td>UI and Interaction</td>
    <td>Radix UI primitives, lucide-react, framer-motion, React Query, Zustand</td>
    <td>Supports accessible controls, polished motion, server state, and lightweight client session state.</td>
  </tr>
  <tr>
    <td>Backend Services</td>
    <td>Go 1.22</td>
    <td>Used for clear service boundaries, typed request handling, and a stable API layer for auth, chat, memory, and gateway routing.</td>
  </tr>
  <tr>
    <td>Agentic Service</td>
    <td>Python 3.11+, FastAPI, LangGraph-style workflow modules</td>
    <td>Handles agent orchestration, guardrails, PHQ-9 flow, CBT routing, memory extraction, STT, and TTS.</td>
  </tr>
  <tr>
    <td>Database</td>
    <td>Postgres with pgvector</td>
    <td>Stores users, sessions, messages, audit records, assessments, vector memory, and operational state.</td>
  </tr>
  <tr>
    <td>Knowledge Graph</td>
    <td>Neo4j</td>
    <td>Represents personal memories, emotions, thoughts, topics, triggers, people, and relationships between them.</td>
  </tr>
  <tr>
    <td>Voice</td>
    <td>OpenAI transcription, ElevenLabs TTS, OpenAI TTS fallback</td>
    <td>Supports multilingual voice input, natural spoken response, and provider fallback when quota or service errors happen.</td>
  </tr>
  <tr>
    <td>Local Orchestration</td>
    <td>Docker Compose</td>
    <td>Runs frontend, Go services, agentic service, Postgres, Redis, Neo4j, migrations, and seeders in one development stack.</td>
  </tr>
</table>

<h2 id="installation-and-run">7. Installation and Run</h2>

<h3>Prerequisites</h3>

<ul>
  <li>Docker and Docker Compose</li>
  <li>Node.js for local frontend work</li>
  <li>Go 1.22 for local backend work</li>
  <li>Python 3.11 or newer for local agentic work</li>
  <li>OpenAI API key for LLM, transcription, embeddings, and OpenAI TTS fallback</li>
  <li>ElevenLabs API key if testing ElevenLabs voice output</li>
</ul>

<h3>Environment</h3>

<pre><code>cp .env.example .env
cp agentic/.env.example agentic/.env
cp backend/.env.example backend/.env
</code></pre>

<p>Set at least:</p>

<pre><code>OPENAI_API_KEY=your_key
AGENTIC_GATEWAY_PRIVATE_KEY=dev-secret
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
</code></pre>

<h3>Run the full development stack</h3>

<pre><code>docker compose -f docker-compose.dev.yml up -d --build
</code></pre>

<h3>Run stack, migrations, and seed scenarios</h3>

<pre><code>./scripts/run_all.sh
</code></pre>

<p>Run only selected seed scenarios:</p>

<pre><code>SEED_SCENARIOS="scenario_1 scenario_3" ./scripts/run_all.sh
</code></pre>

<h3>Local service URLs</h3>

<table>
  <tr>
    <th>Service</th>
    <th>URL</th>
  </tr>
  <tr>
    <td>Frontend</td>
    <td><code>http://localhost:3000</code></td>
  </tr>
  <tr>
    <td>Backend Gateway</td>
    <td><code>http://localhost:3001/api</code></td>
  </tr>
  <tr>
    <td>Agentic Service</td>
    <td><code>http://localhost:8000</code></td>
  </tr>
  <tr>
    <td>Neo4j Browser</td>
    <td><code>http://localhost:7474</code>, user <code>neo4j</code>, password <code>yourpassword</code></td>
  </tr>
  <tr>
    <td>Postgres</td>
    <td><code>localhost:5433</code>, user <code>companion</code>, database <code>companion_chatbot</code></td>
  </tr>
</table>

<h3>Useful checks</h3>

<pre><code>cd frontend &amp;&amp; npx tsc --noEmit
.venv/bin/python -m pytest agentic/tests/test_feature_bot/test_voice
cd backend &amp;&amp; go test ./...
</code></pre>

</details>

<!-- <hr />

<p><strong>Production security note:</strong> before deploying AXIS, review <a href="docs/security-production-ready.md">docs/security-production-ready.md</a> for CORS, JWT, HttpOnly cookie, CSRF, Agentic exposure, rate limiting, monitoring, and security header requirements. Review <a href="docs/backup-production.md">docs/backup-production.md</a> for Postgres, pgvector, Neo4j, and migration-state backups.</p>

<hr /> -->

<details>
<summary id="bahasa-indonesia"><strong>Bahasa Indonesia</strong></summary>

<h2>1. Nama Project</h2>

<p><strong>AXIS Companion</strong> adalah aplikasi companionship chatbot dengan memori jangka panjang berbasis knowledge graph untuk membantu percakapan reflektif, eksplorasi memori personal, dan dukungan emosional ringan bagi mahasiswa.</p>

<h2>2. Deskripsi Project</h2>

<p>AXIS Companion dikembangkan sebagai produk tugas akhir oleh <strong>Mohammad Nugraha Eka Prawira (me)</strong>, Teknik Informatika, Institut Teknologi Bandung (ITB), angkatan 2022. Produk ini mengeksplorasi bagaimana sistem percakapan dapat menjadi ruang yang hangat, terstruktur, dan aman bagi mahasiswa untuk berbicara, berefleksi, dan memahami pola emosional yang berulang.</p>

<h2>3. Problem yang Diselesaikan</h2>

<p>Banyak mahasiswa menghadapi stres, kesepian, tekanan akademik, dan beban emosional, tetapi tidak selalu memiliki ruang yang mudah diakses untuk memproses pengalaman tersebut. AXIS mencoba mengisi ruang antara journaling yang terasa sendiri dan alat klinis yang bisa terasa terlalu formal.</p>

<ul>
  <li>Menyediakan pengalaman interaksi suara yang natural untuk Bahasa Indonesia, English, dan percakapan campuran.</li>
  <li>Menyimpan konteks percakapan agar user tidak perlu mengulang cerita dari awal.</li>
  <li>Menampilkan memori emosional dalam bentuk knowledge graph personal.</li>
  <li>Menyediakan guardrail dan hotline ketika muncul sinyal krisis.</li>
  <li>Memisahkan frontend, backend, dan agentic workflow agar sistem mudah dikembangkan.</li>
</ul>

<h2>4. Fitur Utama</h2>

<ul>
  <li><strong>Dashboard</strong>: ringkasan produk, catatan penting, dan konteks tugas akhir.</li>
  <li><strong>Chat</strong>: percakapan Markdown, voice input, transkrip yang bisa diedit, dan hotline card.</li>
  <li><strong>Voice Room</strong>: ruang fokus dengan mic feedback, transkrip live, dan jawaban suara dari AI.</li>
  <li><strong>Memory Library</strong>: daftar memori personal dengan overlay detail.</li>
  <li><strong>Knowledge Graph</strong>: visualisasi node dan relasi memori dengan warna yang mudah dibedakan.</li>
  <li><strong>PHQ-9 Flow</strong>: alur screening mood dengan penyimpanan skor dan safety handling.</li>
  <li><strong>CBT-style Support</strong>: validasi, psychoeducation, self-compassion, dan grounding.</li>
  <li><strong>Crisis Guardrails</strong>: deteksi krisis, eskalasi, dan resource hotline.</li>
  <li><strong>Session Finalizer</strong>: ringkasan percakapan idle atau panjang menjadi memori.</li>
</ul>

<h2>5. Screenshot</h2>

<p>Screenshot asli dapat ditempatkan di folder <code>docs/screenshots/</code> dengan nama berikut: <code>dashboard.png</code>, <code>chat.png</code>, <code>voice-room.png</code>, <code>memories.png</code>, <code>knowledge-graph.png</code>, <code>hotlines.png</code>, dan <code>settings-profile.png</code>.</p>

<h2>6. Tech Stack dan Alasan</h2>

<ul>
  <li><strong>Next.js, React, TypeScript, Tailwind CSS</strong>: UI modern, responsive, dan typed.</li>
  <li><strong>Go</strong>: backend service yang jelas, cepat, dan mudah dipisah per domain.</li>
  <li><strong>Python Agentic Service</strong>: workflow AI, guardrail, STT, TTS, PHQ-9, CBT, dan memory extraction.</li>
  <li><strong>Postgres + pgvector</strong>: penyimpanan user, session, message, audit, assessment, dan vector memory.</li>
  <li><strong>Neo4j</strong>: knowledge graph untuk memori personal dan relasi emosional.</li>
  <li><strong>Docker Compose</strong>: menjalankan seluruh stack development secara konsisten.</li>
</ul>

<h2>7. Cara Install dan Run</h2>

<pre><code>cp .env.example .env
cp agentic/.env.example agentic/.env
cp backend/.env.example backend/.env
</code></pre>

<pre><code>docker compose -f docker-compose.dev.yml up -d --build
</code></pre>

<p>Untuk menjalankan stack, migration, dan seeder scenario:</p>

<pre><code>./scripts/run_all.sh
</code></pre>

<p>URL lokal utama:</p>

<ul>
  <li>Frontend: <code>http://localhost:3000</code></li>
  <li>Backend Gateway: <code>http://localhost:3001/api</code></li>
  <li>Agentic: <code>http://localhost:8000</code></li>
  <li>Neo4j Browser: <code>http://localhost:7474</code></li>
  <li>Postgres: <code>localhost:5433</code></li>
</ul>

</details>

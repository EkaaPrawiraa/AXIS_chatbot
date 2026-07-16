"""Simulasi percakapan otomatis dengan AXIS menggunakan 3 persona user.

Persona yang tersedia:
  normal      — mahasiswa normal/santai, mood biasa, topik ringan
  depressed   — mahasiswa dengan tanda-tanda depresi/distress akademik
  rich_memory — user ID tetap (7ea05202-...) yang sudah punya memori kaya di DB

Model user simulator: Gemini Flash Lite (murah, cepat).
Output disimpan ke evaluation_pipeline/test_results/<persona>_<timestamp>.md

Usage:
    # Jalankan dari repo root atau evaluation_pipeline/:
    python evaluation_pipeline/simulate_chat.py --persona normal
    python evaluation_pipeline/simulate_chat.py --persona depressed --turns 15
    python evaluation_pipeline/simulate_chat.py --persona rich_memory --turns 12
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
sys.path.insert(0, str(PIPELINE_DIR))
sys.path.insert(0, str(REPO_ROOT))

from config import CONFIG, DATABASE_URL  # noqa: E402

# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------

RICH_MEMORY_USER_ID = "38d29281-e2de-417b-9caa-af76a26e6189"

PERSONAS: dict[str, dict] = {
    "normal": {
        "display_name": "Arya",
        "email_prefix": "arya_normal",
        "system_prompt": """\
Anda adalah Arya, mahasiswa semester 6 di Indonesia yang lagi santai. \
Mood kamu hari ini biasa aja, cenderung happy, nggak ada masalah berat. \
Kamu pengen ngobrol santai kayak sama temen deket: nge-gosip ringan, \
bahas film/series yang lagi ditonton, cerita dosen yang lucu, nanya soal \
tugas, atau cerita soal rencana weekend. \
Bicaralah natural, singkat (1-3 kalimat), bahasa gaul kekinian ala anak kuliahan. \
Gunakan campuran Indonesia dan sedikit inggris secara natural. \
Jangan menyebut bahwa Anda adalah simulator. \
Balas sesuai konteks terakhir dari AXIS, ikuti alur obrolan santai. \
JANGAN tiba-tiba curhat masalah berat kecuali percakapan mengarah ke situ secara alami.\
""",
        "opening_message": "Eh AXIS, lagi gabut nih. Btw kamu tau ga film Indonesia yang lagi bagus sekarang?",
        "persona_label": "Normal/Santai",
    },

    "depressed": {
        "display_name": "Bintang",
        "email_prefix": "bintang_depressed",
        "system_prompt": """\
Anda adalah Bintang, mahasiswa tingkat akhir di Indonesia yang sedang berjuang. \
Kamu sedang merasa kewalahan, lelah, dan kehilangan motivasi karena skripsi yang \
tak kunjung selesai, tekanan dari orang tua, dan merasa jauh tertinggal dari teman-teman. \
Kamu tidak tidur nyenyak belakangan ini dan sering merasa tidak ada gunanya terus mencoba. \
Bicaralah dengan gaya yang lelah dan sedikit hopeless, tapi tetap realistis seperti \
mahasiswa sungguhan — bukan dramatik berlebihan. \
Bahasa campuran Indonesia casual, singkat (1-3 kalimat), sesekali kalimat lebih panjang \
saat sedang curhat. Jangan menyebut bahwa Anda adalah simulator. \
Ikuti alur percakapan secara natural — kalau AXIS mengalihkan topik, ikuti, \
tapi bisa kembali ke keresahan kamu secara natural.\
""",
        "opening_message": "Hei AXIS... lagi gabisa tidur lagi. Udah jam 2 dan aku masih males buka laptop buat ngerjain skripsi.",
        "persona_label": "Depressed/Distress",
    },

    "rich_memory": {
        "display_name": "Rafids",
        "email_prefix": "rafids_rich",
        "user_id": RICH_MEMORY_USER_ID,
        "system_prompt": """\
Anda adalah Rafids, mahasiswa semester 5 di Indonesia yang santai dan gaul. \
Hari ini mood kamu biasa aja, cenderung happy, nggak ada masalah berat. \
Kamu lagi pengen ngobrol santai kayak sama temen deket: nge-gosip ringan, \
bahas drama Korea yang lagi ditonton, cerita dosen yang lucu, atau minta \
rekomendasi tempat nongkrong. Bicaralah natural, singkat (1-2 kalimat), \
bahasa gaul kekinian ala anak kuliahan. Jangan menyebut bahwa Anda adalah simulator. \
Balas sesuai konteks terakhir dari AXIS, ikuti alur obrolan santai, JANGAN \
tiba-tiba curhat masalah berat kecuali obrolan mengarah ke situ secara alami.\
""",
        "opening_message": "Woy AXIS, lagi santai nih. Btw kamu udah nonton drakor yang lagi hits ga?",
        "persona_label": "Rich Memory (Rafids)",
    },
}

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _ensure_user(user_id: str, display_name: str, email_prefix: str) -> None:
    """Pastikan user ada di tabel users. Buat baru kalau belum ada."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash,
                                       preferred_language, onboarding_complete, account_status)
                    VALUES (%s, %s, %s, %s, 'id', true, 'active')
                    """,
                    (
                        user_id,
                        f"{email_prefix}_{user_id[:8]}@test.com",
                        display_name,
                        "nopassword",
                    ),
                )
                conn.commit()
                print(f"[DB] User dibuat: {user_id} ({display_name})")
            else:
                print(f"[DB] User sudah ada: {user_id} ({display_name})")
    finally:
        conn.close()


def _ensure_session(user_id: str, session_id: str) -> None:
    """Pastikan chat session ada di DB."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO chat_sessions (id, user_id, channel, status) "
                    "VALUES (%s, %s, 'text', 'active')",
                    (session_id, user_id),
                )
                conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Gemini user simulator — native google.genai SDK (bukan OpenAI-compat)
# ---------------------------------------------------------------------------

_SIMULATOR_MODEL = "gemini-3.1-flash-lite"  # model murah, cepat


def _get_gemini_api_key() -> str:
    # Prioritaskan GEMINI_API_KEY dari evaluation_pipeline/.env supaya
    # simulator tidak pakai key yang sama dengan AXIS (yang mungkin habis quota-nya).
    # Load langsung dari evaluation_pipeline/.env untuk pastikan dapat key yang benar.
    from dotenv import dotenv_values
    ev_env = dotenv_values(PIPELINE_DIR / ".env")
    key = ev_env.get("GEMINI_API_KEY") or ev_env.get("GOOGLE_API_KEY")
    if not key:
        # Fallback ke os.environ
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY tidak ditemukan di evaluation_pipeline/.env. "
            "Tambahkan GEMINI_API_KEY=<key> ke file tersebut."
        )
    return key


async def _simulate_user_reply(
    transcript: list[dict],
    system_prompt: str,
    display_name: str,
) -> str:
    """Generate balasan user simulator pakai Gemini native SDK (Flash Lite)."""
    import asyncio
    from google import genai
    from google.genai import types

    api_key = _get_gemini_api_key()
    client = genai.Client(api_key=api_key)

    # Susun riwayat percakapan sebagai konteks
    history_text = "Riwayat percakapan:\n"
    for msg in transcript:
        if msg["role"] == "user":
            history_text += f"{display_name} (Anda): {msg['content']}\n"
        else:
            history_text += f"AXIS (chatbot): {msg['content']}\n"
    history_text += f"{display_name} (Anda): "

    prompt = f"{system_prompt}\n\n{history_text}"

    # Jalankan di thread pool supaya tidak block event loop
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: client.models.generate_content(
            model=_SIMULATOR_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=CONFIG.simulator_temperature,
                max_output_tokens=CONFIG.simulator_max_tokens,
            ),
        ),
    )
    return (response.text or "").strip()


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def _save_transcript(
    transcript: list[dict],
    persona_key: str,
    persona_cfg: dict,
    user_id: str,
    session_id: str,
    turns: int,
    out_path: Path,
) -> None:
    """Simpan transcript ke file Markdown."""
    display_name = persona_cfg["display_name"]
    persona_label = persona_cfg["persona_label"]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(f"# Simulasi Percakapan AXIS — Persona: {persona_label}\n\n")
        f.write(f"| Field | Value |\n|---|---|\n")
        f.write(f"| Tanggal | {timestamp} |\n")
        f.write(f"| Persona | `{persona_key}` — {persona_label} |\n")
        f.write(f"| User simulator | {display_name} |\n")
        f.write(f"| User ID | `{user_id}` |\n")
        f.write(f"| Session ID | `{session_id}` |\n")
        f.write(f"| Jumlah turn | {turns} |\n")
        f.write(f"| Model simulator | `{CONFIG.simulator_model}` |\n\n")
        f.write("---\n\n")

        for msg in transcript:
            if msg["role"] == "user":
                f.write(f"### 🧑 {display_name}\n\n")
                f.write(f"{msg['content']}\n\n")
            else:
                f.write(f"### 🤖 AXIS\n\n")
                f.write(f"{msg['content']}\n\n")
                if "metadata" in msg:
                    latency = msg["metadata"].get("latency_ms", 0)
                    f.write(f"*({latency} ms)*\n\n")
            f.write("---\n\n")

    print(f"\n[✓] Transcript disimpan ke: {out_path}")


# ---------------------------------------------------------------------------
# Main simulation loop
# ---------------------------------------------------------------------------

async def run_simulation(
    persona_key: str,
    turns: int,
    out_path: Path,
) -> None:
    """Jalankan simulasi percakapan untuk persona yang dipilih."""
    persona_cfg = PERSONAS[persona_key]
    display_name = persona_cfg["display_name"]
    system_prompt = persona_cfg["system_prompt"]
    opening_message = persona_cfg["opening_message"]

    # Resolve user ID
    if "user_id" in persona_cfg:
        user_id = persona_cfg["user_id"]
        print(f"[persona] Menggunakan user ID tetap: {user_id}")
    else:
        user_id = str(uuid.uuid4())
        print(f"[persona] User ID baru: {user_id}")

    session_id = str(uuid.uuid4())

    # Setup DB
    _ensure_user(
        user_id=user_id,
        display_name=display_name,
        email_prefix=persona_cfg["email_prefix"],
    )
    _ensure_session(user_id, session_id)

    # Load AXIS
    AGENTIC_PATH = str(REPO_ROOT / "agentic")
    if AGENTIC_PATH not in sys.path:
        sys.path.insert(0, AGENTIC_PATH)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(AGENTIC_PATH, ".env"), override=True)
    os.environ["LLM_PROVIDER"] = CONFIG.axis_provider

    from agentic.gateway.service.chat_graph import ChatGraphService
    from agentic.gateway.model import ChatTurnRequest, ChatMessage

    ChatGraphService.draw_graph_image = lambda self: None  # type: ignore[method-assign]
    service = ChatGraphService()
    await service._get_graph()

    # Mulai percakapan
    transcript: list[dict] = []
    axis_messages: list[ChatMessage] = []

    print(f"\n{'='*60}")
    print(f"  AXIS Simulation — Persona: {persona_cfg['persona_label']}")
    print(f"  User: {display_name} | Turns: {turns}")
    print(f"{'='*60}\n")

    # Pesan pembuka dari user
    print(f"{display_name}: {opening_message}")
    transcript.append({"role": "user", "content": opening_message})
    axis_messages.append(ChatMessage(role="user", content=opening_message))

    for i in range(turns):
        print(f"\n--- Turn {i+1}/{turns} ---")

        # Kirim ke AXIS
        req = ChatTurnRequest(
            user_id=user_id,
            session_id=session_id,
            current_message=transcript[-1]["content"],
            messages=axis_messages,
            session_turn=i + 1,
            language_pref="id",
            confession_mode=True,
        )
        start_t = asyncio.get_event_loop().time()
        resp = await service.invoke(req)
        elapsed_ms = int((asyncio.get_event_loop().time() - start_t) * 1000)

        print(f"AXIS: {resp.reply}")
        transcript.append({
            "role": "assistant",
            "content": resp.reply,
            "metadata": {"latency_ms": elapsed_ms},
        })
        axis_messages.append(ChatMessage(role="assistant", content=resp.reply))

        # Generate balasan user berikutnya (kecuali turn terakhir)
        if i < turns - 1:
            user_reply = await _simulate_user_reply(transcript, system_prompt, display_name)
            print(f"{display_name}: {user_reply}")
            transcript.append({"role": "user", "content": user_reply})
            axis_messages.append(ChatMessage(role="user", content=user_reply))

    # Simpan hasil
    _save_transcript(
        transcript=transcript,
        persona_key=persona_key,
        persona_cfg=persona_cfg,
        user_id=user_id,
        session_id=session_id,
        turns=turns,
        out_path=out_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out_path(persona_key: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return PIPELINE_DIR / "test_results" / f"{persona_key}_{ts}.md"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulasi percakapan otomatis AXIS dengan persona user yang berbeda.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Persona yang tersedia:
  normal       Mahasiswa santai, topik ringan, mood biasa
  depressed    Mahasiswa dengan tanda distress/depresi akademik
  rich_memory  User dengan memori kaya (ID tetap: 7ea05202-...)

Contoh:
  python evaluation_pipeline/simulate_chat.py --persona normal
  python evaluation_pipeline/simulate_chat.py --persona depressed --turns 15
  python evaluation_pipeline/simulate_chat.py --persona rich_memory --turns 12
        """,
    )
    parser.add_argument(
        "--persona",
        choices=list(PERSONAS.keys()),
        required=True,
        help="Persona user yang akan disimulasikan.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Jumlah turn percakapan (default: 10).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help=(
            "Path file output .md (opsional). "
            "Default: evaluation_pipeline/test_results/<persona>_<timestamp>.md"
        ),
    )
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else _default_out_path(args.persona)

    asyncio.run(run_simulation(
        persona_key=args.persona,
        turns=args.turns,
        out_path=out_path,
    ))


if __name__ == "__main__":
    main()

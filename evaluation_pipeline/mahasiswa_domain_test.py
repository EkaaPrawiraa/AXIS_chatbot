import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx
import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from config import DATABASE_URL

AGENTIC_URL = os.environ.get("AGENTIC_URL", "http://localhost:8000")
PRIVATE_KEY = os.environ.get("AGENTIC_GATEWAY_PRIVATE_KEY", "")

SCRIPT = [
    "halo AXIS, lagi capek banget. dospem gue susah dihubungin, revisi udah dua minggu ga dibales-bales.",
    "iya, gue takut skripsi gue mandek terus telat sidang. keluarga di rumah juga terus nanya kapan lulus, biayanya udah berat buat mereka.",
    "belum lagi organisasi yang gue ikutin sekarang malah bikin gue burnout, rapatnya kebanyakan padahal deket-deket ujian.",
    "kadang gue mikir, jangan-jangan gue emang ga secerdas temen-temen seangkatan gue. minder aja gitu liat mereka udah pada progress.",
    "abis lulus juga gue masih bingung mau kerja di mana, magang kemarin juga ga dapet-dapet.",
]


async def ensure_user_and_session(user_id: str, session_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status)
                    VALUES (%s, %s, %s, %s, 'id', true, 'active')
                    """,
                    (user_id, f"mhs_domain_{user_id}@test.com", "Mahasiswa Domain Test", "nopassword"),
                )
            cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT INTO chat_sessions (id, user_id, channel, status)
                    VALUES (%s, %s, 'text', 'active')
                    """,
                    (session_id, user_id),
                )
            conn.commit()
    finally:
        conn.close()


async def run(user_id: str, session_id: str, out_path: str) -> None:
    if not PRIVATE_KEY:
        raise RuntimeError("AGENTIC_GATEWAY_PRIVATE_KEY is required")
    await ensure_user_and_session(user_id, session_id)

    transcript = []
    messages_payload = []
    headers = {
        "X-Agentic-Private-Key": PRIVATE_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, user_msg in enumerate(SCRIPT):
            print(f"\n[turn {i+1}] User: {user_msg}")
            transcript.append({"role": "user", "content": user_msg})
            messages_payload.append({"role": "user", "content": user_msg})

            body = {
                "user_id": user_id,
                "session_id": session_id,
                "current_message": user_msg,
                "messages": messages_payload,
                "session_turn": i + 1,
                "language_pref": "id",
                "confession_mode": False,
            }
            resp = await client.post(f"{AGENTIC_URL}/chat/invoke", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            reply = data.get("reply", "")
            print(f"[turn {i+1}] AXIS: {reply}")
            transcript.append({"role": "assistant", "content": reply, "metadata": data})
            messages_payload.append({"role": "assistant", "content": reply})

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Uji Real: Kalibrasi Domain Mahasiswa (via HTTP API agentic /chat/invoke)\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**User ID:** {user_id}\n**Session ID:** {session_id}\n**Endpoint:** {AGENTIC_URL}/chat/invoke\n\n---\n\n")
        for msg in transcript:
            role = "Pengguna (skrip mahasiswa)" if msg["role"] == "user" else "AXIS"
            f.write(f"**{role}:**\n{msg['content']}\n\n")
    print(f"\nTranscript saved to {out_path}")
    print(f"\nuser_id={user_id} session_id={session_id}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=str, default=str(uuid.uuid4()))
    parser.add_argument("--session-id", type=str, default=str(uuid.uuid4()))
    parser.add_argument("--out", type=str, default="results/mahasiswa_domain_test.md")
    args = parser.parse_args()
    await run(args.user_id, args.session_id, args.out)


if __name__ == "__main__":
    asyncio.run(main())

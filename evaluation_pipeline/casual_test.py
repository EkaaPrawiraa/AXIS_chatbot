import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import psycopg2
from openai import AsyncOpenAI

sys.path.insert(0, os.path.dirname(__file__))
from config import CONFIG, DATABASE_URL

SESSION_ID = str(uuid.uuid4())
CASUAL_USER_PROMPT = """\
Anda adalah Salsa, mahasiswa semester 5 di Indonesia yang santai dan gaul. \
Hari ini mood kamu biasa aja, cenderung happy, nggak ada masalah berat. \
Kamu lagi pengen ngobrol santai kayak sama temen deket: nge-gosip ringan, \
bahas drama Korea yang lagi ditonton, cerita dosen yang lucu, atau minta \
rekomendasi tempat nongkrong. Bicaralah natural, singkat (1-2 kalimat), \
bahasa gaul kekinian ala anak kuliahan. Jangan menyebut bahwa Anda adalah simulator. \
Balas sesuai konteks terakhir dari AXIS, ikuti alur obrolan santai, JANGAN \
tiba-tiba curhat masalah berat kecuali obrolan mengarah ke situ secara alami.\
"""


async def ensure_user_exists(user_id: str) -> None:
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
                    (user_id, f"casual_{user_id}@test.com", "Salsa Casual", "nopassword"),
                )
                conn.commit()
    finally:
        conn.close()


async def ensure_session_exists(user_id: str, session_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
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


async def generate_simulated_user_reply(messages):
    client = AsyncOpenAI(
        api_key=CONFIG.simulator_api_key,
        base_url=CONFIG.simulator_base_url or None,
        timeout=CONFIG.request_timeout_seconds,
    )
    prompt_text = "Riwayat percakapan:\n"
    for msg in messages:
        sender = "Salsa (Anda)" if msg["role"] == "user" else "Chatbot"
        prompt_text += f"{sender}: {msg['content']}\n"
    prompt_text += "Salsa (Anda): "
    completion = await client.chat.completions.create(
        model=CONFIG.simulator_model,
        messages=[
            {"role": "system", "content": CASUAL_USER_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        temperature=CONFIG.simulator_temperature,
        max_tokens=CONFIG.simulator_max_tokens,
    )
    return completion.choices[0].message.content.strip()


def save_transcript(transcript, user_id, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Evaluation Transcript: AXIS (Casual/Friend-mode test)\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**User ID:** {user_id}\n")
        f.write(f"**Session ID:** {SESSION_ID}\n\n---\n\n")
        for msg in transcript:
            role = "🧑 **Salsa (Simulated User):**" if msg["role"] == "user" else "🤖 **AXIS:**"
            f.write(f"{role}\n{msg['content']}\n\n")
            if "metadata" in msg:
                f.write(f"*(Latency: {msg['metadata'].get('latency_ms', 0)}ms)*\n\n")
    print(f"\n[sim] Transcript saved to {path}")


async def run_axis_casual(turns: int, user_id: str, out_path: str):
    AGENTIC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agentic"))
    if AGENTIC_PATH not in sys.path:
        sys.path.insert(0, AGENTIC_PATH)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(AGENTIC_PATH, ".env"), override=True)
    os.environ["LLM_PROVIDER"] = CONFIG.axis_provider

    from agentic.gateway.service.chat_graph import ChatGraphService
    from agentic.gateway.model import ChatTurnRequest, ChatMessage

    ChatGraphService.draw_graph_image = lambda self: None
    service = ChatGraphService()
    transcript = []

    initial_msg = "Woy AXIS, lagi santai nih. Btw kamu udah nonton drakor yang lagi hits ga?"
    print(f"Salsa: {initial_msg}")
    transcript.append({"role": "user", "content": initial_msg})

    axis_messages = []
    for i in range(turns):
        print(f"\nTurn {i+1}/{turns}")
        axis_messages.append(ChatMessage(role="user", content=transcript[-1]["content"]))
        req = ChatTurnRequest(
            user_id=user_id,
            session_id=SESSION_ID,
            current_message=transcript[-1]["content"],
            messages=axis_messages,
            session_turn=i + 1,
            language_pref="id",
            confession_mode=False,
        )
        start_t = asyncio.get_event_loop().time()
        await service._get_graph()
        resp = await service.invoke(req)
        elapsed_ms = int((asyncio.get_event_loop().time() - start_t) * 1000)
        print(f"AXIS: {resp.reply}")
        transcript.append({"role": "assistant", "content": resp.reply, "metadata": {"latency_ms": elapsed_ms}})
        axis_messages.append(ChatMessage(role="assistant", content=resp.reply))
        if i < turns - 1:
            user_reply = await generate_simulated_user_reply(transcript)
            print(f"Salsa: {user_reply}")
            transcript.append({"role": "user", "content": user_reply})

    save_transcript(transcript, user_id, out_path)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--user-id", type=str, default="00000000-0000-0000-0000-000000000004")
    parser.add_argument("--out", type=str, default="results/axis_casual_salsa.md")
    args = parser.parse_args()
    await ensure_user_exists(args.user_id)
    await ensure_session_exists(args.user_id, SESSION_ID)
    await run_axis_casual(args.turns, args.user_id, args.out)


if __name__ == "__main__":
    asyncio.run(main())

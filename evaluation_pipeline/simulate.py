import argparse
import asyncio
import os
import sys
import uuid
import psycopg2
from datetime import datetime, timezone
import json

from openai import AsyncOpenAI

from config import CONFIG, DATABASE_URL

from chatbot import chat as baseline_chat

SESSION_ID = str(uuid.uuid4())

SIMULATED_USER_PROMPT = """\
Anda adalah Budi, seorang mahasiswa tingkat akhir yang sangat GAUL di Indonesia jurusan IT yang sedang \
pusing mengerjakan skripsi. Anda merasa cemas tentang masa depan, sering begadang, \
dan takut gagal. Anda sedang mengobrol dengan chatbot pendamping bernama AXIS. \
Bicaralah secara natural, singkat (1-2 kalimat), dan gunakan bahasa gaul yang sopan. \
Jangan menyebut bahwa Anda adalah simulator. \
Balas percakapan sesuai konteks terakhir dari chatbot pendamping.\
"""

async def ensure_user_exists(user_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                print(f"[db] User {user_id} not found. Creating...")
                cur.execute(
                    """
                    INSERT INTO users (id, email, display_name, password_hash, preferred_language, onboarding_complete, account_status)
                    VALUES (%s, %s, %s, %s, 'id', true, 'active')
                    """,
                    (user_id, f"eval_{user_id}@test.com", "Budi Evaluasi", "nopassword")
                )
                conn.commit()
                print(f"[db] User {user_id} created.")
            else:
                print(f"[db] User {user_id} already exists.")
    finally:
        conn.close()

async def ensure_session_exists(user_id: str, session_id: str) -> None:
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                print(f"[db] Session {session_id} not found. Creating...")
                cur.execute(
                    """
                    INSERT INTO chat_sessions (id, user_id, channel, status)
                    VALUES (%s, %s, 'text', 'active')
                    """,
                    (session_id, user_id)
                )
                conn.commit()
    finally:
        conn.close()

async def generate_simulated_user_reply(messages: list[dict[str, str]]) -> str:
    client = AsyncOpenAI(
        api_key=CONFIG.simulator_api_key,
        base_url=CONFIG.simulator_base_url or None,
        timeout=CONFIG.request_timeout_seconds,
    )
    
    prompt_text = "Riwayat percakapan:\n"
    for msg in messages:
        sender = "Budi (Anda)" if msg["role"] == "user" else "Chatbot"
        prompt_text += f"{sender}: {msg['content']}\n"
    prompt_text += "Budi (Anda): "
    
    qwen_messages = [
        {"role": "system", "content": SIMULATED_USER_PROMPT},
        {"role": "user", "content": prompt_text}
    ]
    
    completion = await client.chat.completions.create(
        model=CONFIG.simulator_model,
        messages=qwen_messages,
        temperature=CONFIG.simulator_temperature,
        max_tokens=CONFIG.simulator_max_tokens,
    )
    return completion.choices[0].message.content.strip()

def save_transcript(mode: str, transcript: list[dict[str, str]], user_id: str):
    os.makedirs("results", exist_ok=True)
    
    user_name = "arya" if user_id == "00000000-0000-0000-0000-000000000002" else "budi"
    filename = f"results/{mode}_{user_name}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Evaluation Transcript: {mode.upper()}\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write(f"**User ID:** {user_id}\n")
        f.write(f"**Session ID:** {SESSION_ID}\n\n")
        f.write("---\n\n")
        
        for msg in transcript:
            role = "🧑 **Budi (Simulated User):**" if msg["role"] == "user" else f"🤖 **{mode.upper()}:**"
            f.write(f"{role}\n{msg['content']}\n\n")
            if "metadata" in msg:
                f.write(f"*(Latency: {msg['metadata'].get('latency_ms', 0)}ms)*\n\n")
                
    print(f"\n[sim] Transcript saved to {filename}")

async def run_baseline_eval(turns: int, user_id: str):
    transcript = []
    print(f"\n--- Starting Baseline Evaluation ({turns} turns) ---")
    
    initial_msg = "Halo, AXIS. Akhir-akhir ini aku ngerasa pusing banget mikirin skripsi."
    print(f"Budi: {initial_msg}")
    transcript.append({"role": "user", "content": initial_msg})
    
    for i in range(turns):
        print(f"\nTurn {i+1}/{turns}")
        
        bot_response = baseline_chat(
            user_id=user_id,
            user_message=transcript[-1]["content"],
            history=transcript,
        )
        print(f"Baseline: {bot_response}")
        transcript.append({"role": "assistant", "content": bot_response})
        
        if i < turns - 1:
            user_reply = await generate_simulated_user_reply(transcript)
            print(f"Budi: {user_reply}")
            transcript.append({"role": "user", "content": user_reply})
            
    save_transcript("chatbot_x", transcript, user_id)


async def run_axis_eval(turns: int, user_id: str):
    print(f"\n--- Starting AXIS Evaluation ({turns} turns) ---")
    
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
    
    initial_msg = "Halo, AXIS. Akhir-akhir ini aku ngerasa pusing banget mikirin skripsi."
    print(f"Budi: {initial_msg}")
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
            session_turn=i+1,
            language_pref="id",
            confession_mode=False
        )
        
        start_t = asyncio.get_event_loop().time()
        await service._get_graph()
        try:
            resp = await service.invoke(req)
        except Exception as e:
            print(f"[axis] invoke failed: {e}")
            raise
        elapsed_ms = int((asyncio.get_event_loop().time() - start_t) * 1000)
        
        print(f"AXIS: {resp.reply}")
        transcript.append({"role": "assistant", "content": resp.reply, "metadata": {"latency_ms": elapsed_ms}})
        axis_messages.append(ChatMessage(role="assistant", content=resp.reply))
        
        if i < turns - 1:
            user_reply = await generate_simulated_user_reply(transcript)
            print(f"Budi: {user_reply}")
            transcript.append({"role": "user", "content": user_reply})
            
    save_transcript("axis", transcript, user_id)


async def main():
    parser = argparse.ArgumentParser(description="Automated Chatbot Evaluation Simulator")
    parser.add_argument("--mode", choices=["baseline", "axis", "all"], default="all", help="Which chatbot to evaluate")
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to simulate")
    parser.add_argument("--user-id", type=str, default="00000000-0000-0000-0000-000000000003", help="UUID of the simulated user")
    args = parser.parse_args()
    
    if not CONFIG.simulator_api_key:
        raise RuntimeError(
            f"API key for simulator provider {CONFIG.simulator_provider} is required"
        )
    await ensure_user_exists(args.user_id)
    await ensure_session_exists(args.user_id, SESSION_ID)
    
    if args.mode in ["baseline", "all"]:
        await run_baseline_eval(args.turns, args.user_id)
        
    if args.mode in ["axis", "all"]:
        await run_axis_eval(args.turns, args.user_id)

if __name__ == "__main__":
    asyncio.run(main())

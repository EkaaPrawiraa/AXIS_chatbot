import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

from openai import OpenAI

from config import OPENAI_API_KEY, CHAT_MODEL, TOP_K_DEFAULT
from retrieval import retrieve_memories

_openai_client = OpenAI(api_key=OPENAI_API_KEY)

_LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")

SYSTEM_PROMPT_TEMPLATE = """\
You are AXIS, a compassionate AI companion. Your role is to provide emotional support, \
engage in meaningful conversation, and help the user reflect on their experiences.

Below are relevant memories retrieved from the user's history. Use them to personalize \
your response and maintain continuity, but do not directly quote or enumerate them unless \
it feels natural to do so.

--- Relevant Memories ---
{memories}
--- End of Memories ---

Respond warmly, empathetically, and concisely."""


def _format_memories(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "(No relevant memories found.)"
    lines = []
    for i, m in enumerate(memories, 1):
        score = f"{m['similarity']:.3f}"
        lines.append(f"{i}. [{m['table']}] (similarity={score}) {m['content']}")
    return "\n".join(lines)


def _log_entry(
    user_id: str,
    user_message: str,
    memories: List[Dict[str, Any]],
    system_prompt: str,
    response: str,
) -> None:
    os.makedirs(_LOGS_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = os.path.join(_LOGS_DIR, f"{user_id}_{date_str}.json")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "user_message": user_message,
        "retrieved_memories": memories,
        "system_prompt": system_prompt,
        "response": response,
    }

    existing: List[Dict[str, Any]] = []
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing.append(entry)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"[chatbot] Log saved → {log_file}")


def chat(user_id: str, user_message: str, top_k: int = TOP_K_DEFAULT) -> str:
    memories = retrieve_memories(user_id, user_message, top_k=top_k)

    memory_text = _format_memories(memories)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(memories=memory_text)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    completion = _openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.7,
    )

    response = completion.choices[0].message.content or ""

    _log_entry(user_id, user_message, memories, system_prompt, response)

    return response

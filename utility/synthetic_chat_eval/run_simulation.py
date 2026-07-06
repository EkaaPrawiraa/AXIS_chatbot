"""utility/synthetic_chat_eval/run_simulation.py

Synthetic chat simulation harness for AXIS.

Usage:
  # Seed then simulate
  python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --seed --simulate --turns 10

  # Seed only
  python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --seed

  # Simulate only (assumes user already seeded and logged in)
  python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --simulate --turns 8

  # Purge seed data for a scenario
  python -m utility.synthetic_chat_eval.run_simulation --scenario stressed --purge

Environment variables:
  CHATBOT_BASE_URL        Gateway base URL  (default: http://localhost:8080)
  OPENAI_API_KEY          Required for --simulate
  LLM_SIMULATOR_MODEL     OpenAI model id   (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any

import httpx

_BASE_DIR = Path(__file__).parent
_OUTPUT_DIR = _BASE_DIR / "output"

_SCENARIOS: dict[str, str] = {
    "stressed": "utility.synthetic_chat_eval.users.stressed_user",
    "normal":   "utility.synthetic_chat_eval.users.normal_user",
    "happy":    "utility.synthetic_chat_eval.users.happy_user",
}



def _base_url() -> str:
    return os.getenv("CHATBOT_BASE_URL", "http://localhost:8080")


def _openai_model() -> str:
    return os.getenv("LLM_SIMULATOR_MODEL", "gpt-4o")


def _load_scenario(name: str):
    if name not in _SCENARIOS:
        raise SystemExit(f"Unknown scenario '{name}'. Choose from: {', '.join(_SCENARIOS)}")
    return import_module(_SCENARIOS[name])


def _timestamp() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")



def _login(email: str, password: str) -> tuple[str, dict[str, str]]:
    """
    POST /api/auth/login and return (access_token, cookie_jar).
    The server sets a JWT in a cookie; we also grab it from response body.
    """
    url = f"{_base_url()}/api/auth/login"
    resp = httpx.post(url, json={"email": email, "password": password}, follow_redirects=True)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Login failed [{resp.status_code}]: {resp.text[:300]}")

    body = resp.json()
    token = (
        body.get("data", {}).get("token")
        or body.get("token")
        or ""
    )
    cookies = dict(resp.cookies)
    print(f"  [auth] logged in as {email} (token={'present' if token else 'cookie-only'})")
    return token, cookies



def _start_conversation(token: str, cookies: dict[str, str]) -> str:
    """POST /api/conversations — returns conversation_id."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = httpx.post(
        f"{_base_url()}/api/conversations",
        headers=headers,
        cookies=cookies,
        json={"channel": "text"},
        follow_redirects=True,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"StartConversation failed [{resp.status_code}]: {resp.text[:300]}")
    body = resp.json()
    conv_id = (
        body.get("data", {}).get("id")
        or body.get("data", {}).get("conversation_id")
        or body.get("id")
        or body.get("conversation_id")
    )
    if not conv_id:
        raise RuntimeError(f"Could not parse conversation_id from: {body}")
    print(f"  [chat] started conversation: {conv_id}")
    return conv_id


def _stream_message(
    conversation_id: str,
    message: str,
    token: str,
    cookies: dict[str, str],
) -> str:
    """
    POST /api/conversations/{conversation_id}/messages/stream via SSE.
    Collects all 'data:' lines and reconstructs the full assistant text.
    Returns the assembled assistant reply.
    """
    url = f"{_base_url()}/api/conversations/{conversation_id}/messages/stream"
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    chunks: list[str] = []
    with httpx.stream(
        "POST",
        url,
        headers=headers,
        cookies=cookies,
        json={"message": message},
        timeout=120.0,
    ) as resp:
        if resp.status_code not in (200, 201):
            body = resp.read()
            raise RuntimeError(f"StreamMessage failed [{resp.status_code}]: {body[:300]}")
        for line in resp.iter_lines():
            line = line.strip()
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload in ("[DONE]", ""):
                    continue
                try:
                    obj = json.loads(payload)
                    delta = (
                        obj.get("choices", [{}])[0].get("delta", {}).get("content")
                        or obj.get("content")
                        or obj.get("text")
                        or obj.get("data")
                        or ""
                    )
                    if delta:
                        chunks.append(delta)
                except json.JSONDecodeError:
                    chunks.append(payload)

    return "".join(chunks)



def _simulate_next_user_message(
    persona_system_prompt: str,
    conversation_history: list[dict[str, str]],
    openai_client,
) -> str:
    """
    Call OpenAI to generate the next user turn given conversation history
    and persona system prompt.
    """
    messages = [{"role": "system", "content": persona_system_prompt}]
    for turn in conversation_history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "system",
        "content": (
            "Berdasarkan konteks percakapan di atas, tuliskan pesan berikutnya dari "
            "perspektif kamu (pengguna). Jangan sertakan label atau prefix apapun — "
            "tuliskan hanya teks pesan itu sendiri, seolah kamu mengetiknya langsung. "
            "Jaga konsistensi karakter dan emosi sesuai persona."
        ),
    })

    resp = openai_client.chat.completions.create(
        model=_openai_model(),
        messages=messages,
        max_tokens=300,
        temperature=0.85,
    )
    return resp.choices[0].message.content.strip()



async def _run_seed(scenario_module, purge: bool = False) -> None:
    from agentic.memory.neo4j_client import init_client
    from utility.synthetic_chat_eval._common import (
        SeedConfig, _is_uuid, _purge_namespace, _session_ids_for_namespace,
    )

    cfg_dict = scenario_module.PERSONA_CONFIG
    user_id    = cfg_dict["user_id"]
    namespace  = cfg_dict["namespace"]
    pw_hash    = cfg_dict.get("password_hash", "")

    if not _is_uuid(user_id):
        raise SystemExit(f"user_id '{user_id}' is not a valid UUID")

    seed_cfg = SeedConfig(
        user_id=user_id,
        namespace=namespace,
        password_hash=pw_hash,
        preferred_language="id",
    )

    await init_client()

    if purge:
        session_ids = list(_session_ids_for_namespace(namespace, count=3).values())
        await _purge_namespace(namespace, session_ids, user_id=user_id)
        print(f"Purged namespace: {namespace}")
        return

    print(f"Seeding user '{cfg_dict['name']}' (namespace={namespace}) ...")
    await scenario_module.seed_user(seed_cfg)



def _run_simulate(scenario_module, turns: int) -> None:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Install openai: pip install openai") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY env var is required for --simulate")

    openai_client = OpenAI(api_key=api_key)
    cfg = scenario_module.PERSONA_CONFIG
    opening_messages: list[str] = scenario_module.OPENING_MESSAGES

    print(f"\nStarting simulation: scenario={cfg['name']}, turns={turns}")
    print(f"  Chatbot URL : {_base_url()}")
    print(f"  LLM model   : {_openai_model()}")

    token, cookies = _login(cfg["email"], cfg["password"])
    conversation_id = _start_conversation(token, cookies)

    history: list[dict[str, str]] = []
    log: list[dict[str, Any]] = []

    for turn_idx in range(turns):
        if turn_idx < len(opening_messages):
            user_msg = opening_messages[turn_idx]
        else:
            print(f"\n  [turn {turn_idx+1}/{turns}] generating user message via LLM ...")
            user_msg = _simulate_next_user_message(
                cfg["persona_system_prompt"],
                history,
                openai_client,
            )

        print(f"\n  [turn {turn_idx+1}/{turns}] USER  → {user_msg[:120]}")
        t_start = time.perf_counter()

        try:
            assistant_reply = _stream_message(conversation_id, user_msg, token, cookies)
        except Exception as exc:
            print(f"  [turn {turn_idx+1}/{turns}] ERROR: {exc}")
            assistant_reply = f"[ERROR: {exc}]"

        elapsed = time.perf_counter() - t_start
        print(f"  [turn {turn_idx+1}/{turns}] AXIS  → {assistant_reply[:120]} ({elapsed:.1f}s)")

        history.append({"role": "user",      "content": user_msg})
        history.append({"role": "assistant", "content": assistant_reply})
        log.append({
            "turn": turn_idx + 1,
            "user":      user_msg,
            "assistant": assistant_reply,
            "latency_s": round(elapsed, 3),
        })

    _save_log(cfg, conversation_id, log)


def _save_log(cfg: dict, conversation_id: str, log: list[dict[str, Any]]) -> None:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = _OUTPUT_DIR / f"{cfg['scenario_name']}_{_timestamp()}.json"
    payload = {
        "scenario": cfg["name"],
        "scenario_name": cfg["scenario_name"],
        "user_id": cfg["user_id"],
        "conversation_id": conversation_id,
        "phq9_baseline": cfg.get("phq9_baseline"),
        "generated_at": _timestamp(),
        "turns": log,
    }
    filename.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n  Log saved → {filename}")



def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="AXIS synthetic chat evaluation harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--scenario",
        required=True,
        choices=list(_SCENARIOS.keys()),
        help="Which user persona to use",
    )
    ap.add_argument("--seed",     action="store_true", help="Pre-seed KG + Postgres for the scenario")
    ap.add_argument("--simulate", action="store_true", help="Run automated LLM-simulated conversation")
    ap.add_argument("--purge",    action="store_true", help="Delete seeded data for the scenario")
    ap.add_argument("--turns",    type=int, default=8, help="Number of conversation turns (default: 8)")
    return ap


def main() -> int:
    ap = _build_parser()
    args = ap.parse_args()

    if not any([args.seed, args.simulate, args.purge]):
        ap.print_help()
        return 2

    if args.purge and (args.seed or args.simulate):
        raise SystemExit("--purge cannot be combined with --seed or --simulate")

    scenario_module = _load_scenario(args.scenario)

    if args.seed or args.purge:
        asyncio.run(_run_seed(scenario_module, purge=args.purge))

    if args.simulate:
        _run_simulate(scenario_module, turns=args.turns)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

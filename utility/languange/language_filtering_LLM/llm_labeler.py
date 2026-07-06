"""Optional LLM labeling stage for filtered slang entries."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    temperature: float = 0.0
    max_tokens: int = 400
    sleep_s: float = 0.5


SYSTEM_PROMPT = (
    "You label Indonesian student slang terms for mental-health context. "
    "Return ONLY valid JSON with keys: category, emotional_weight, distress_signal, "
    "escalation_flag, clinical_note, definition_id. "
    "category must be L1|L2|L3|L4. emotional_weight: low|medium|high. "
    "distress_signal/escalation_flag: boolean. "
    "definition_id should be a short Bahasa Indonesian definition."
)


def _call_openai(messages: list[dict[str, str]], cfg: LLMConfig) -> dict[str, Any]:
    body = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "messages": messages,
    }
    req = Request(
        OPENAI_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=60000000) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def label_entry(entry: dict, cfg: LLMConfig, *, overwrite_existing: bool = False) -> dict:
    term = entry.get("term", "")
    definition = entry.get("definition_id", "")
    examples = entry.get("usage_examples", [])
    user_prompt = (
        f"Term: {term}\n"
        f"Definition: {definition}\n"
        f"Examples: {examples}\n"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    label = _call_openai(messages, cfg)
    out = dict(entry)
    out["llm_label"] = label

    # By default preserve existing values from previous stages.
    # If overwrite_existing=True, trust LLM label as the canonical value.
    for key in (
        "category",
        "emotional_weight",
        "distress_signal",
        "escalation_flag",
        "clinical_note",
        "definition_id",
    ):
        if overwrite_existing and key in label:
            out[key] = label[key]
            continue
        if not out.get(key) and key in label:
            out[key] = label[key]
    return out


def label_entries(entries: list[dict], cfg: LLMConfig, *, overwrite_existing: bool = False) -> list[dict]:
    labeled: list[dict] = []
    print(len(entries))
    for entry in entries:
        try:
            labeled.append(label_entry(entry, cfg, overwrite_existing=overwrite_existing))
        except (HTTPError, URLError, json.JSONDecodeError) as exc:
            out = dict(entry)
            out["llm_label_error"] = str(exc)
            labeled.append(out)
        time.sleep(cfg.sleep_s)
    return labeled


def load_config_from_env() -> LLMConfig:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    print(api_key)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for LLM labeling")
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    return LLMConfig(api_key=api_key, model=model)

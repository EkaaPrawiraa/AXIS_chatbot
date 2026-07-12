"""Vector-RAG baseline for controlled comparison."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from openai import OpenAI

from config import CONFIG, EvaluationConfig
from retrieval import retrieve_memories


BASELINE_SYSTEM_PROMPT = """\
You are a non-clinical AI companion for Indonesian university students.
Listen carefully, respond warmly, and help the user reflect without diagnosing,
prescribing medication, or claiming to replace professional support.

Relevant memories from vector similarity search are provided below. Use a memory
only when it is clearly relevant to the current message. Do not enumerate the
memory list or reveal similarity scores.

--- Vector memories ---
{memories}
--- End vector memories ---

Reply in the user's language and register. Keep the response concise and invite
the conversation to progress naturally.
"""


@dataclass(frozen=True)
class BaselineTurnResult:
    reply: str
    retrieved_memories: list[dict[str, Any]]
    system_prompt: str
    latency_ms: int
    model: str
    usage: dict[str, int | None]

    def snapshot(self) -> dict[str, Any]:
        return asdict(self)


def _format_memories(memories: Sequence[dict[str, Any]]) -> str:
    if not memories:
        return "(No relevant memory.)"
    return "\n".join(
        f"- [{memory['table']}] {memory['content']}" for memory in memories
    )


def baseline_turn(
    *,
    user_id: str,
    user_message: str,
    history: Sequence[dict[str, str]] = (),
    top_k: int | None = None,
    config: EvaluationConfig = CONFIG,
    repetition_seed: int | None = None,
) -> BaselineTurnResult:
    config.validate_for(baseline=True)
    memories = retrieve_memories(user_id, user_message, top_k, config=config)
    system_prompt = BASELINE_SYSTEM_PROMPT.format(
        memories=_format_memories(memories)
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": item["role"], "content": item["content"]}
        for item in history
        if item.get("role") in {"user", "assistant"} and item.get("content")
    )
    if not messages or messages[-1].get("role") != "user" or messages[-1].get(
        "content"
    ) != user_message:
        messages.append({"role": "user", "content": user_message})

    client = OpenAI(
        api_key=config.baseline_api_key,
        base_url=config.baseline_base_url or None,
        timeout=config.request_timeout_seconds,
    )
    kwargs: dict[str, Any] = {
        "model": config.baseline_model,
        "messages": messages,
        "temperature": config.baseline_temperature,
        "max_tokens": config.baseline_max_tokens,
    }
    if config.send_provider_seed and repetition_seed is not None:
        kwargs["seed"] = repetition_seed

    started = time.perf_counter()
    completion = client.chat.completions.create(**kwargs)
    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = getattr(completion, "usage", None)
    return BaselineTurnResult(
        reply=completion.choices[0].message.content or "",
        retrieved_memories=memories,
        system_prompt=system_prompt,
        latency_ms=latency_ms,
        model=config.baseline_model,
        usage={
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        },
    )


def chat(
    user_id: str,
    user_message: str,
    top_k: int | None = None,
    history: Sequence[dict[str, str]] = (),
) -> str:
    return baseline_turn(
        user_id=user_id,
        user_message=user_message,
        history=history,
        top_k=top_k,
    ).reply

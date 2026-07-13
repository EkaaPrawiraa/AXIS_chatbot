"""minimalkan metrik"""

from __future__ import annotations

from collections import Counter
from threading import Lock
from typing import Any


_lock = Lock()
_counters: Counter[str] = Counter()
_latency_ms: Counter[str] = Counter()
_llm_tokens: Counter[str] = Counter()


def increment(name: str, **labels: Any) -> None:
    with _lock:
        _counters[_key(name, labels)] += 1


def observe_latency(name: str, elapsed_ms: int, **labels: Any) -> None:
    with _lock:
        _latency_ms[_key(name, labels)] += max(0, int(elapsed_ms))


def observe_http_request(method: str, path: str, status: int, elapsed_ms: int) -> None:
    labels = {"method": method, "path": path, "status": status}
    increment("http_requests_total", **labels)
    observe_latency("http_request_latency_ms_total", elapsed_ms, **labels)
    if status >= 400:
        increment("http_errors_total", **labels)


def observe_llm_usage(model: str | None, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    label = {"model": model or "unknown"}
    with _lock:
        _llm_tokens[_key("llm_prompt_tokens_total", label)] += max(0, int(prompt_tokens))
        _llm_tokens[_key("llm_completion_tokens_total", label)] += max(0, int(completion_tokens))


def observe_langchain_usage(response: Any, *, fallback_model: str | None = None) -> None:
    metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}
    model = (
        response_metadata.get("model_name")
        or response_metadata.get("model")
        or fallback_model
    )
    prompt = (
        metadata.get("input_tokens")
        or token_usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or 0
    )
    completion = (
        metadata.get("output_tokens")
        or token_usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or 0
    )
    observe_llm_usage(model, prompt_tokens=int(prompt or 0), completion_tokens=int(completion or 0))


def snapshot() -> dict[str, dict[str, int]]:
    with _lock:
        return {
            "counters": dict(_counters),
            "latency_ms_total": dict(_latency_ms),
            "llm_tokens": dict(_llm_tokens),
        }


def _key(name: str, labels: dict[str, Any]) -> str:
    if not labels:
        return name
    suffix = ",".join(f"{k}={labels[k]}" for k in sorted(labels))
    return f"{name}{{{suffix}}}"

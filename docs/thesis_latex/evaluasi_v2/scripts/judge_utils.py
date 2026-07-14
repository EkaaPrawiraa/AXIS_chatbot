"""Small reproducible helpers for the thesis LLM-as-judge evaluations."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
JUDGE_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")
# The adjudication pass has a separate instruction and request. It currently
# reuses the stronger judge model, so reports must not call it a third
# independent base model.
ADJUDICATOR_MODEL = "gemini-2.5-flash"


def load_project_env() -> None:
    for path in (ROOT / ".env", ROOT / "agentic" / ".env", ROOT / "evaluation_pipeline" / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            os.environ[key.strip()] = value.strip().strip("'\"")


def call_json(*, model: str, prompt: str, max_output_tokens: int = 4000) -> Any:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini API key is unavailable for LLM-as-judge evaluation")
    # Keep the SDK client alive until the synchronous request has completed.
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    raw = (getattr(response, "text", "") or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    start = next((index for index, char in enumerate(raw) if char in "[{"), None)
    if start is None:
        raise ValueError(f"{model} did not return JSON: {raw[:300]!r}")
    try:
        value, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        Path("/tmp/axis_llm_judge_invalid_json.txt").write_text(raw, encoding="utf-8")
        raise ValueError(f"{model} returned malformed JSON; raw response saved to /tmp/axis_llm_judge_invalid_json.txt") from exc
    return value


def consensus_rows(
    *,
    prompt: str,
    id_key: str = "id",
    max_output_tokens: int = 4000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run two blind judge configurations and adjudicate only disagreements."""
    outputs: dict[str, list[dict[str, Any]]] = {}
    for model in JUDGE_MODELS:
        result = call_json(model=model, prompt=prompt, max_output_tokens=max_output_tokens)
        if not isinstance(result, list):
            raise ValueError(f"{model} did not return a JSON list")
        outputs[model] = [dict(row) for row in result]

    by_model = {
        model: {str(row[id_key]): row for row in rows if id_key in row}
        for model, rows in outputs.items()
    }
    ids = set.intersection(*(set(rows) for rows in by_model.values()))
    first, second = JUDGE_MODELS
    disagreements = [
        ident for ident in sorted(ids)
        if {k: v for k, v in by_model[first][ident].items() if k != id_key}
        != {k: v for k, v in by_model[second][ident].items() if k != id_key}
    ]

    adjudicated: dict[str, dict[str, Any]] = {}
    if disagreements:
        subset = [by_model[first][ident] for ident in disagreements]
        adjudication_prompt = (
            "Anda adalah adjudikator. Dua penilai independen berbeda pada beberapa "
            "label berikut. Tentukan label akhir dengan menerapkan rubrik dari prompt "
            "asal secara konsisten. Kembalikan HANYA JSON array dan pertahankan id.\n\n"
            f"PROMPT ASAL:\n{prompt}\n\n"
            f"KELUARAN PENILAI 1:\n{json.dumps(subset, ensure_ascii=False)}\n"
            f"KELUARAN PENILAI 2:\n{json.dumps([by_model[second][i] for i in disagreements], ensure_ascii=False)}"
        )
        result = call_json(model=ADJUDICATOR_MODEL, prompt=adjudication_prompt, max_output_tokens=max_output_tokens)
        if not isinstance(result, list):
            raise ValueError("adjudicator did not return a JSON list")
        adjudicated = {str(row[id_key]): dict(row) for row in result if id_key in row}

    consensus = [adjudicated.get(ident, by_model[first][ident]) for ident in sorted(ids)]
    metadata = {
        "judge_models": list(JUDGE_MODELS),
        "adjudicator_model": ADJUDICATOR_MODEL if disagreements else None,
        "n_rows": len(consensus),
        "n_disagreements": len(disagreements),
        "disagreement_ids": disagreements,
        "raw_judges": outputs,
    }
    return consensus, metadata


def consensus_batched(
    *,
    items: list[dict[str, Any]],
    build_prompt: Any,
    batch_size: int = 10,
    id_key: str = "id",
    max_output_tokens: int = 4000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply blind judging in small batches so every case receives a complete label."""
    rows: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    for start in range(0, len(items), batch_size):
        batch = items[start:start + batch_size]
        consensus, metadata = consensus_rows(
            prompt=build_prompt(batch),
            id_key=id_key,
            max_output_tokens=max_output_tokens,
        )
        rows.extend(consensus)
        batches.append(metadata)
    return rows, {
        "judge_models": list(JUDGE_MODELS),
        "adjudicator_model": ADJUDICATOR_MODEL,
        "n_rows": len(rows),
        "n_batches": len(batches),
        "n_disagreements": sum(batch["n_disagreements"] for batch in batches),
        "batches": batches,
    }

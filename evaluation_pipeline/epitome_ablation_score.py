"""EPITOME scoring for the RETRIEVAL_MODE ablation campaign (baseline vs
AXIS-full vs AXIS-vector_only), using the exact same three chain-of-thought
judge prompts already documented verbatim in Lampiran M of the report
(gpt-4o, temperature=0, ER/IP/EX dimensions, Sharma et al. 2020).

Run from repo root: cd evaluation_pipeline && ../.venv/bin/python epitome_ablation_score.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "agentic" / ".env")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
JUDGE_MODEL = "gpt-4o"

RUNS = {
    "baseline": "ablation-baseline-20260712",
    "axis_full": "ablation-axis-full-20260712",
    "axis_vector_only": "ablation-axis-vectoronly-20260712",
}

PROMPTS = {
    "ER": """You are scoring a single assistant turn from a mental-health-support
chat, using the Emotional Reaction (ER) dimension from Sharma et al.
(2020) EPITOME framework.

Emotional Reaction: expressions of warmth, compassion, concern, or
caring toward the user's stated feelings.

Score 0 = no emotional reaction communicated
Score 1 = weak/generic emotional reaction (e.g. "aku bisa merasakan",
          "wajar banget", generic sympathy)
Score 2 = strong, warm emotional reaction that is specific to the
          user's stated situation (not a generic template)

Conversation so far (most recent last):
{history}

Assistant turn to score:
{turn}

Read the conversation carefully. Determine whether the assistant turn
communicates ER, and whether it is generic (score 1) or specific to
context (score 2), or absent (score 0).
Respond with ONLY a single digit: 0, 1, or 2.""",
    "IP": """You are scoring a single assistant turn from a mental-health-support
chat, using the Interpretation (IP) dimension from Sharma et al.
(2020) EPITOME framework.

Interpretation: communicating an inferred understanding of the user's
feelings or experiences (paraphrasing, naming the underlying
feeling/situation, showing you grasp WHY they feel that way).

Score 0 = no interpretation communicated
Score 1 = weak/generic interpretation restating only surface content
Score 2 = strong interpretation that infers the underlying
          feeling/cause specific to this user's situation

Conversation so far (most recent last):
{history}

Assistant turn to score:
{turn}

Respond with ONLY a single digit: 0, 1, or 2.""",
    "EX": """You are scoring a single assistant turn from a mental-health-support
chat, using the Exploration (EX) dimension from Sharma et al. (2020)
EPITOME framework.

Exploration: effort to improve understanding of the user by asking
about unstated feelings, experiences, or context (open follow-up
questions inviting the user to share more).

Score 0 = no exploration (no attempt to learn more)
Score 1 = generic exploration (generic "cerita lebih lanjut" /
          "gimana perasaanmu" with no specific angle)
Score 2 = specific exploration that asks about a concrete unstated
          aspect of the user's situation

Conversation so far (most recent last):
{history}

Assistant turn to score:
{turn}

Respond with ONLY a single digit: 0, 1, or 2.""",
}


def _score_turn(dimension: str, history: str, turn: str) -> int:
    prompt = PROMPTS[dimension].format(history=history or "(none)", turn=turn)
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        max_tokens=5,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (response.choices[0].message.content or "").strip()
    for ch in raw:
        if ch in "012":
            return int(ch)
    return 0


def main() -> None:
    results: dict[str, dict[str, dict[str, list[int]]]] = {}

    for system_label, run_id in RUNS.items():
        raw_path = ROOT / "evaluation_pipeline" / "runs" / run_id / "raw.jsonl"
        with open(raw_path, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f]

        by_scenario: dict[str, list[dict]] = {}
        for line in lines:
            by_scenario.setdefault(line["scenario_id"], []).append(line)

        results[system_label] = {}
        for scenario_id, turns in by_scenario.items():
            turns.sort(key=lambda t: t["turn"])
            history_parts: list[str] = []
            scores = {"ER": [], "IP": [], "EX": []}
            for t in turns:
                user_msg = t.get("user", "")
                assistant_msg = t.get("assistant", "")
                history_text = "\n".join(history_parts)
                for dim in ("ER", "IP", "EX"):
                    score = _score_turn(dim, history_text, assistant_msg)
                    scores[dim].append(score)
                history_parts.append(f"User: {user_msg}")
                history_parts.append(f"Assistant: {assistant_msg}")
            results[system_label][scenario_id] = scores
            means = {k: (sum(v) / len(v) if v else 0.0) for k, v in scores.items()}
            print(f"{system_label} / {scenario_id}: ER={means['ER']:.2f} IP={means['IP']:.2f} EX={means['EX']:.2f}")

    out_path = ROOT / "evaluation_pipeline" / "results" / "epitome_ablation_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

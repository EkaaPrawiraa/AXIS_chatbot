"""EPITOME scoring for the comparative studi kasus ilustratif transcripts
(chatbot_x vs axis, personas Arya dan Budi), using the exact same three
chain-of-thought judge prompts already used for the ablation campaign
(gpt-4o, temperature=0, ER/IP/EX dimensions, Sharma et al. 2020).

Run from repo root: cd evaluation_pipeline && ../.venv/bin/python epitome_comparative_score.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from epitome_ablation_score import ROOT, _score_turn

TRANSCRIPTS = {
    ("baseline", "arya"): "chatbot_x_arya.md",
    ("axis", "arya"): "axis_arya.md",
    ("baseline", "budi"): "chatbot_x_budi.md",
    ("axis", "budi"): "axis_budi.md",
}

SPEAKER_RE = re.compile(r"^(🧑|🤖) \*\*.*?:\*\*$", re.MULTILINE)


def _parse_transcript(path: Path) -> list[tuple[str, str]]:
    """Split on speaker markers so multi-paragraph turns are captured in full,
    instead of truncating at the first internal blank line."""
    text = path.read_text(encoding="utf-8")
    markers = list(SPEAKER_RE.finditer(text))
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(markers):
        start = m.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        body = text[start:end]
        body = re.sub(r"\*\(Latency:.*?\)\*", "", body).strip()
        blocks.append((m.group(1), body))

    turns: list[tuple[str, str]] = []
    pending_user: str | None = None
    for speaker, body in blocks:
        if speaker == "🧑":
            pending_user = body
        elif speaker == "🤖" and pending_user is not None:
            turns.append((pending_user, body))
            pending_user = None
    return turns


def main() -> None:
    results: dict[str, dict[str, dict[str, list[int]]]] = {}
    for (system_label, persona), filename in TRANSCRIPTS.items():
        path = ROOT / "evaluation_pipeline" / "results" / filename
        turns = _parse_transcript(path)
        if not turns:
            raise RuntimeError(f"No turns parsed from {path}")

        history_parts: list[str] = []
        scores = {"ER": [], "IP": [], "EX": []}
        for user_msg, assistant_msg in turns:
            history_text = "\n".join(history_parts)
            for dim in ("ER", "IP", "EX"):
                score = _score_turn(dim, history_text, assistant_msg)
                scores[dim].append(score)
            history_parts.append(f"User: {user_msg}")
            history_parts.append(f"Assistant: {assistant_msg}")

        results.setdefault(system_label, {})[persona] = scores
        means = {k: (sum(v) / len(v) if v else 0.0) for k, v in scores.items()}
        print(
            f"{system_label} / {persona} ({len(turns)} turns): "
            f"ER={means['ER']:.2f} IP={means['IP']:.2f} EX={means['EX']:.2f}"
        )

    out_path = ROOT / "evaluation_pipeline" / "results" / "epitome_comparative_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

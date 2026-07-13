"""Second run of the ablation EPITOME scorer, against the Dinda replication
scenario (independent domain from Budi), reusing the exact same prompts."""

from __future__ import annotations

import json

from epitome_ablation_score import ROOT, _score_turn

RUNS = {
    "baseline": "ablation-baseline-replication-20260712",
    "axis_full": "ablation-axis-full-replication-20260712",
    "axis_vector_only": "ablation-axis-vectoronly-replication-20260712",
}


def main() -> None:
    results: dict[str, dict[str, list[int]]] = {}
    for system_label, run_id in RUNS.items():
        raw_path = ROOT / "evaluation_pipeline" / "runs" / run_id / "raw.jsonl"
        with open(raw_path, encoding="utf-8") as f:
            turns = sorted((json.loads(l) for l in f), key=lambda t: t["turn"])

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

        results[system_label] = scores
        means = {k: (sum(v) / len(v) if v else 0.0) for k, v in scores.items()}
        print(f"{system_label}: ER={means['ER']:.2f} IP={means['IP']:.2f} EX={means['EX']:.2f}")

    out_path = ROOT / "evaluation_pipeline" / "results" / "epitome_replication_scores.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

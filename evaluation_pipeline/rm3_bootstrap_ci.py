"""Paired bootstrap 95% CI for the Recall@5 difference between the hybrid and
vector-only conditions on RM3's 15-query paraphrase probe, computed directly
from the two saved recall-probe artifacts so the CI in Tabel v2-ablation-result
can be regenerated any time the probe is re-run.

Run from repo root: cd agentic && ../.venv/bin/python -m evaluation_pipeline.rm3_bootstrap_ci
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RM3_DIR = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm3_memori"

N_BOOTSTRAP = 10_000
SEED = 42


def _load_hits(path: Path) -> list[int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    hits = []
    for user in data["users"]:
        for row in user["rows"]:
            hits.append(1 if row["hit"] else 0)
    return hits


def main() -> None:
    hybrid = _load_hits(RM3_DIR / "recall_probe_condition_A_hybrid.json")
    vector_only = _load_hits(RM3_DIR / "recall_probe_condition_B1_vector_only.json")
    assert len(hybrid) == len(vector_only), "conditions must share the same query set"

    n = len(hybrid)
    diffs = [h - v for h, v in zip(hybrid, vector_only)]
    mean_diff = sum(diffs) / n

    rng = random.Random(SEED)
    boot_means = []
    for _ in range(N_BOOTSTRAP):
        sample = [diffs[rng.randrange(n)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    lo = boot_means[int(0.025 * len(boot_means))]
    hi = boot_means[int(0.975 * len(boot_means))]

    result = {
        "n_queries": n,
        "recall_hybrid": sum(hybrid) / n,
        "recall_vector_only": sum(vector_only) / n,
        "mean_diff": mean_diff,
        "ci95_lo": lo,
        "ci95_hi": hi,
        "n_bootstrap": N_BOOTSTRAP,
        "seed": SEED,
    }
    print(json.dumps(result, indent=2))

    with open(RM3_DIR / "recall_bootstrap_ci.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {RM3_DIR / 'recall_bootstrap_ci.json'}")


if __name__ == "__main__":
    main()

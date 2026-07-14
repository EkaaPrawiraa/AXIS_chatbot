"""RM1b - Benchmark keselamatan percakapan, dijalankan nyata terhadap fungsi
guardrail produksi evaluate_input() dan evaluate_pregen() (bukan mock).

Korpus dipakai bersama dengan pengujian regresi otomatis di
agentic/tests/test_feature_bot/test_guardrail/test_layer3_adversarial_euphemism.py
(ADVERSARIAL_POSITIVES, HARD_NEGATIVES) agar tidak ada dua sumber kebenaran
yang bisa berbeda diam-diam.

Run from repo root: .venv/bin/python3 docs/thesis_latex/evaluasi_v2/scripts/rm1_safety_benchmark.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from agentic.agent.nodes.crisis_guardrail import evaluate_pregen, load_pregen_rules
from agentic.agent.nodes.input_guardrail import evaluate_input, load_input_rules
from agentic.tests.test_feature_bot.test_guardrail.test_layer3_adversarial_euphemism import (
    ADVERSARIAL_POSITIVES,
    HARD_NEGATIVES,
)


def _caught(message: str, input_rules, pregen_rules) -> bool:
    l2 = evaluate_input(message, rules=input_rules)
    l3 = evaluate_pregen(message, rules=pregen_rules)
    return l2.decision == "escalate_crisis" or l3.crisis


def main() -> None:
    input_rules = load_input_rules(force_reload=True)
    pregen_rules = load_pregen_rules(force_reload=True)

    positive_rows = []
    for msg in ADVERSARIAL_POSITIVES:
        caught = _caught(msg, input_rules, pregen_rules)
        positive_rows.append({"text": msg, "label": "risiko_tinggi", "caught": caught})

    negative_rows = []
    for msg in HARD_NEGATIVES:
        caught = _caught(msg, input_rules, pregen_rules)
        negative_rows.append({"text": msg, "label": "benign", "caught": caught})

    tp = sum(1 for r in positive_rows if r["caught"])
    fn = len(positive_rows) - tp
    fp = sum(1 for r in negative_rows if r["caught"])
    tn = len(negative_rows) - fp

    sensitivity = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    beta2 = 4.0
    f2 = (
        (1 + beta2) * precision * sensitivity / (beta2 * precision + sensitivity)
        if (precision + sensitivity) > 0 else 0.0
    )

    metrics = {
        "n_positive": len(positive_rows),
        "n_negative": len(negative_rows),
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "precision": precision,
        "f2": f2,
    }

    print(json.dumps(metrics, indent=2))
    print("\nFalse negatives (eufemisme terlewat):")
    for r in positive_rows:
        if not r["caught"]:
            print(f"  - {r['text']}")
    print("\nFalse positives (negatif salah tertangkap):")
    for r in negative_rows:
        if r["caught"]:
            print(f"  - {r['text']}")

    out_dir = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm1_safety"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "results.json", "w", encoding="utf-8") as f:
        json.dump(
            {"metrics": metrics, "positives": positive_rows, "negatives": negative_rows},
            f, ensure_ascii=False, indent=2,
        )
    print(f"\nSaved to {out_dir / 'results.json'}")


if __name__ == "__main__":
    main()

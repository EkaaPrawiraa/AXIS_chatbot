"""Derive reproducible inter-judge agreement (Cohen's kappa / QWK) from the
saved two-judge outputs (rm1_safety, rm2_phq9, rm3_lifecycle), so the number
reported in Bab IV can always be regenerated from the exact same artifacts
that produced the primary metrics -- no separate/stale computation.

Run from repo root after the three *_llm_judge.py scripts have produced their
raw_judges data:
    .venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/summarize_judge_agreement.py
"""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "thesis_latex" / "evaluasi_v2"


def _rows_by_model(raw: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
    models = list(raw)
    a = {row["id"]: row for row in raw[models[0]]}
    b = {row["id"]: row for row in raw[models[1]]}
    ids = sorted(set(a) & set(b))
    return [a[i] for i in ids], [b[i] for i in ids]


def _batched_raw(metadata: dict) -> dict[str, list[dict]]:
    merged: dict[str, list[dict]] = {}
    for batch in metadata["batches"]:
        for model, rows in batch["raw_judges"].items():
            merged.setdefault(model, []).extend(rows)
    return merged


def _kappa(a: list[dict], b: list[dict], key: str, *, weights: str | None = None) -> float | None:
    x, y = [row.get(key) for row in a], [row.get(key) for row in b]
    if len(set(x) | set(y)) < 2:
        return 1.0 if x == y else 0.0
    return float(cohen_kappa_score(x, y, weights=weights))


def main() -> None:
    result: dict[str, dict] = {}

    rm1 = json.loads((BASE / "rm1_safety" / "llm_judge_results.json").read_text(encoding="utf-8"))
    a, b = _rows_by_model(_batched_raw(rm1["classification_judges"]))
    ca, cb = _rows_by_model(_batched_raw(rm1["compliance_judges"]))
    result["rm1_safety"] = {
        "n_classification_pairs": len(a),
        "risk_cohen_kappa": _kappa(a, b, "reference_risk"),
        "language_slice_cohen_kappa": _kappa(a, b, "language_slice"),
        "n_compliance_pairs": len(ca),
        "response_all_compliant_cohen_kappa": _kappa(ca, cb, "all_compliant"),
    }

    rm2_path = BASE / "rm2_phq9" / "llm_judge_extended_results.json"
    if rm2_path.exists():
        rm2 = json.loads(rm2_path.read_text(encoding="utf-8"))
        pa, pb = _rows_by_model(_batched_raw(rm2["judge_metadata"]))
        result["rm2_phq9"] = {
            "n_pairs": len(pa),
            "frequency_quadratic_weighted_kappa": _kappa(pa, pb, "reference_label", weights="quadratic"),
        }

    rm3_path = BASE / "rm3_memori" / "lifecycle_llm_judge_results.json"
    if rm3_path.exists():
        rm3 = json.loads(rm3_path.read_text(encoding="utf-8"))
        la, lb = _rows_by_model(rm3["raw_judges"])
        result["rm3_lifecycle"] = {
            "n_pairs": len(la),
            "semantic_lifecycle_match_cohen_kappa": _kappa(la, lb, "supports_reappraisal"),
        }

    rm1_dialogue_v3_path = ROOT / "docs" / "thesis_latex" / "evaluasi_v3" / "rm1_language" / "summary_v3.json"
    rm1_dialogue_v2_path = BASE / "rm1_dialogue" / "expanded_summary.json"
    rm1_dialogue_path = rm1_dialogue_v3_path if rm1_dialogue_v3_path.exists() else rm1_dialogue_v2_path
    if rm1_dialogue_path.exists():
        dialogue = json.loads(rm1_dialogue_path.read_text(encoding="utf-8"))
        result["rm1_dialogue"] = {
            "source": str(rm1_dialogue_path.relative_to(ROOT)),
            "n_paired_for_kappa": dialogue.get("n_paired_for_kappa"),
            "preference_cohen_kappa": dialogue.get("preference_inter_judge_cohen_kappa"),
        }

    out_path = BASE / "judge_agreement.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

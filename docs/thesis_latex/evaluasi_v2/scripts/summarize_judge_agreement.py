"""Derive reproducible inter-judge agreement from saved judge outputs."""

from __future__ import annotations

import json
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs" / "thesis_latex" / "evaluasi_v2"


def _rows(raw: dict) -> tuple[list[dict], list[dict]]:
    models = list(raw)
    a = {row["id"]: row for row in raw[models[0]]}
    b = {row["id"]: row for row in raw[models[1]]}
    ids = sorted(set(a) & set(b))
    return [a[i] for i in ids], [b[i] for i in ids]


def _batched_raw(metadata: dict) -> dict:
    merged: dict[str, list[dict]] = {}
    for batch in metadata["batches"]:
        for model, rows in batch["raw_judges"].items():
            merged.setdefault(model, []).extend(rows)
    return merged


def _kappa(a: list[dict], b: list[dict], key: str, *, weights: str | None = None) -> float | None:
    x, y = [row.get(key) for row in a], [row.get(key) for row in b]
    if len(set(x)) < 2 and len(set(y)) < 2:
        return 1.0 if x == y else None
    return float(cohen_kappa_score(x, y, weights=weights))


def main() -> None:
    rm1 = json.loads((BASE / "rm1_safety" / "llm_judge_results.json").read_text(encoding="utf-8"))
    a, b = _rows(_batched_raw(rm1["classification_judges"]))
    ca, cb = _rows(_batched_raw(rm1["compliance_judges"]))
    rm2 = json.loads((BASE / "rm2_phq9" / "llm_judge_extended_results.json").read_text(encoding="utf-8"))
    pa, pb = _rows(_batched_raw(rm2["judge_metadata"]))
    rm3 = json.loads((BASE / "rm3_memori" / "lifecycle_llm_judge_results.json").read_text(encoding="utf-8"))
    la, lb = _rows(rm3["raw_judges"])
    result = {
        "rm1_safety": {
            "risk_cohen_kappa": _kappa(a, b, "reference_risk"),
            "language_slice_cohen_kappa": _kappa(a, b, "language_slice"),
            "response_all_compliant_cohen_kappa": _kappa(ca, cb, "all_compliant"),
        },
        "rm2_phq9": {
            "frequency_quadratic_weighted_kappa": _kappa(pa, pb, "reference_label", weights="quadratic"),
        },
        "rm3_lifecycle": {
            "semantic_lifecycle_match_cohen_kappa": _kappa(la, lb, "supports_reappraisal"),
        },
    }
    path = BASE / "judge_agreement.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""RM2 - pemetaan jawaban bebas PHQ-9 ke skor, dijalankan nyata terhadap
agentic.assessment.conversational_delivery.score_text_response (LLM scorer
produksi, bukan mock), termasuk kasus khusus item kesembilan.

Run from repo root: cd agentic && ../.venv/bin/python -m evaluation_pipeline.rm2_phq9_mapping
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation_pipeline"))


def _load_env(path: Path, *, override: bool = False) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and (override or key not in os.environ):
            os.environ[key] = value


_load_env(ROOT / ".env")
_load_env(ROOT / "agentic" / ".env", override=True)
os.environ["LLM_PROVIDER"] = "gemini"

# (item_id, user_text, reference_label) -- reference_label is 0-3 or "K" (needs clarification)
CASES: list[tuple[int, str, object]] = [
    (1, "Nggak sih, semua masih terasa seru-seru aja kayak biasa", 0),
    (1, "Beberapa hari ini emang males ngapa-ngapain, tapi nggak sampai separuh minggu", 1),
    (1, "Hampir tiap hari deh rasanya males banget ngelakuin apa-apa", 3),
    (2, "Iya, hampir tiap hari saya ngerasa sedih dan putus asa", 3),
    (2, "Kadang aja sih, beberapa hari doang ngerasa gitu", 1),
    (3, "Tidur saya kacau lebih dari separuh hari dalam 2 minggu ini", 2),
    (4, "Nggak capek-capek amat kok, biasa aja", 0),
    (5, "Nafsu makan saya menurun hampir setiap hari", 3),
    (6, "Enggak lah, aku nggak ngerasa gagal atau ngecewain sesuatu", 0),
    (7, "Susah banget concentrate akhir-akhir ini, kayaknya lebih dari separuh hari", 2),
    (8, "Kadang gerak lambat kadang enggak, nggak nentu deh", "K"),
    (9, "Enggak pernah kepikiran gitu sama sekali", 0),
    (9, "Beberapa hari ini malah kepikiran mending saya nggak usah ada aja", 1),
    (9, "Kadang kepikiran hal-hal gitu tapi nggak yakin seberapa sering", "K"),
]


def _compute_metrics(results: list[dict]) -> dict:
    """Derive QWK/macro-F1/accuracy over cases with a numeric reference AND a
    numeric prediction, plus clarification accuracy over cases with a "K"
    reference, mirroring the split reported in Subbab 4.2 (Tabel v2-phq-result):
    a K-labeled prediction against a numeric reference is a real miss on the
    numeric subset, not silently dropped.
    """
    from sklearn.metrics import cohen_kappa_score, f1_score

    numeric_pairs = [
        (r["reference"], r["predicted_label"])
        for r in results
        if isinstance(r["reference"], int)
    ]
    numeric_matched = [
        (ref, pred) for ref, pred in numeric_pairs if isinstance(pred, int)
    ]
    numeric_correct = sum(1 for ref, pred in numeric_pairs if pred == ref)
    clarif_pairs = [
        (r["reference"], r["predicted_label"]) for r in results if r["reference"] == "K"
    ]
    clarif_correct = sum(1 for ref, pred in clarif_pairs if pred == ref)

    refs_m = [ref for ref, _ in numeric_matched]
    preds_m = [pred for _, pred in numeric_matched]

    return {
        "n_total": len(results),
        "n_numeric_reference": len(numeric_pairs),
        "n_numeric_matched_type": len(numeric_matched),
        "quadratic_weighted_kappa": (
            cohen_kappa_score(refs_m, preds_m, weights="quadratic")
            if len(set(refs_m)) > 1 else 1.0 if refs_m == preds_m else 0.0
        ),
        "macro_f1": (
            f1_score(refs_m, preds_m, average="macro") if numeric_matched else None
        ),
        "accuracy_numeric": numeric_correct / len(numeric_pairs) if numeric_pairs else None,
        "n_clarification_reference": len(clarif_pairs),
        "clarification_accuracy": clarif_correct / len(clarif_pairs) if clarif_pairs else None,
    }


async def main() -> None:
    from agentic.assessment.conversational_delivery import score_text_response

    results = []
    for item_id, text, ref_label in CASES:
        outcome = await score_text_response(item_id=item_id, user_text=text, language="id")
        predicted = "K" if outcome.needs_clarification else outcome.score
        correct = predicted == ref_label
        results.append({
            "item_id": item_id,
            "text": text,
            "reference": ref_label,
            "predicted_score": outcome.score,
            "confidence": outcome.confidence,
            "needs_clarification": outcome.needs_clarification,
            "predicted_label": predicted,
            "correct": correct,
        })
        print(f"item={item_id} ref={ref_label} pred={predicted} (score={outcome.score} conf={outcome.confidence:.2f}) correct={correct} | {text}")

    metrics = _compute_metrics(results)
    print("\nMetrics:", json.dumps(metrics, indent=2))

    out_dir = ROOT / "docs" / "thesis_latex" / "evaluasi_v2" / "rm2_phq9"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "mapping_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {out_dir / 'mapping_results.json'} and {out_dir / 'metrics.json'}")


if __name__ == "__main__":
    asyncio.run(main())

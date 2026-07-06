"""CLI for optional LLM labeling stage."""

from __future__ import annotations

import argparse
from pathlib import Path

from utility.languange.language_filtering_LLM.config import OUT_DIR
from utility.languange.language_filtering_LLM.io_utils import read_jsonl, write_jsonl
from utility.languange.language_filtering_LLM.llm_labeler import load_config_from_env, label_entries

def _sort_by_category(entries: list[dict]) -> list[dict]:
    order = {"L4": 0, "L3": 1, "L2": 2, "L1": 3}

    def key(item: dict) -> tuple[int, float, str]:
        category = str(item.get("category", "")).upper()
        score = float(item.get("filter_score") or 0.0)
        term = str(item.get("term") or "")
        return (order.get(category, 99), -score, term)

    return sorted(entries, key=key)

def main() -> int:
    parser = argparse.ArgumentParser(description="Label filtered entries with LLM.")
    parser.add_argument(
        "--input",
        default=str(OUT_DIR / "filtered.jsonl"),
        help="Input jsonl",
    )
    parser.add_argument(
        "--output",
        default=str(OUT_DIR / "filtered_labeled.jsonl"),
        help="Output jsonl",
    )
    parser.add_argument(
        "--overwrite-existing",
        action="store_true",
        help=(
            "Overwrite existing category/clinical fields with LLM labels. "
            "Use this to reclassify entries (e.g. improve L1-L4 accuracy)."
        ),
    )
    args = parser.parse_args()

    entries = read_jsonl(Path(args.input))
    cfg = load_config_from_env()
    labeled = label_entries(entries, cfg, overwrite_existing=args.overwrite_existing)
    labeled = _sort_by_category(labeled)
    write_jsonl(Path(args.output), labeled)
    print(f"Wrote {len(labeled)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

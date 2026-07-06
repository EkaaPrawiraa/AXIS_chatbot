"""CLI entrypoint for filtering slang + mental-health relevant entries."""

from __future__ import annotations

import argparse
from pathlib import Path

from utility.languange.language_filtering_LLM.config import OUT_DIR, RAW_DIR
from utility.languange.language_filtering_LLM.pipeline import run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter raw slang corpus for student usage.")
    parser.add_argument("--raw-dir", default=str(RAW_DIR), help="Raw jsonl directory")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="Output directory")
    args = parser.parse_args()

    result = run_pipeline(raw_dir=Path(args.raw_dir), out_dir=Path(args.out_dir))
    stats = result.get("stats", {})
    skip = result.get("skip_stats", {}) or {}
    print("Filter completed")
    print(f"- filtered count: {result.get('filtered_count')}")
    print(f"- output: {result.get('output')}")
    print(f"- category breakdown: {stats.get('by_category')}")
    if skip.get("skipped_missing_schema"):
        print(f"- skipped (missing required schema): {skip.get('skipped_missing_schema')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

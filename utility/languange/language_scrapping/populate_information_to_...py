"""Normalize and export the linguistic corpus for application injection."""

from __future__ import annotations

import argparse
from pathlib import Path

from utility.languange.language_scrapping.config import OUT_DIR, RAW_DIR
from utility.languange.language_scrapping.pipeline import run_pipeline


def main() -> int:
	parser = argparse.ArgumentParser(description="Build linguistic corpus outputs.")
	parser.add_argument(
		"--input-jsonl",
		default=None,
		help="Optional single jsonl file to use as input (overrides --raw-dir)",
	)
	parser.add_argument(
		"--raw-dir",
		default=str(RAW_DIR),
		help="Directory containing raw jsonl inputs",
	)
	parser.add_argument(
		"--out-dir",
		default=str(OUT_DIR),
		help="Output directory for corpus and prompt snippet",
	)
	args = parser.parse_args()

	raw_dir = Path(args.input_jsonl) if args.input_jsonl else (Path(args.raw_dir) if args.raw_dir else RAW_DIR)
	out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
	result = run_pipeline(raw_dir=raw_dir, out_dir=out_dir)
	stats = result.get("stats", {})
	print("Pipeline completed")
	print(f"- total entries: {stats.get('total', 0)}")
	print(f"- prompt entries: {result.get('prompt_entry_count', 0)}")
	print(f"- output dir: {out_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

"""End-to-end builder for linguistic_ready.jsonl.

Flow:
1) Ingest/scrape raw sources into language_scrapping/data/raw
2) Run rule-based filtering
3) Run LLM labeling (optionally overwrite existing labels)
4) Write final linguistic_ready.jsonl
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRAPE_SCRIPT = REPO_ROOT / "utility/languange/language_scrapping/scrape_from_...py"
FILTER_SCRIPT = REPO_ROOT / "utility/languange/language_filtering_LLM/run_filter.py"
LABEL_SCRIPT = REPO_ROOT / "utility/languange/language_filtering_LLM/run_llm_label.py"
DEFAULT_READY_OUT = REPO_ROOT / "utility/languange/data_ready_to_fed/linguistic_ready.jsonl"
DEFAULT_LABELED = REPO_ROOT / "utility/languange/language_filtering_LLM/out/filtered_labeled.jsonl"


def _run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build final linguistic_ready.jsonl end-to-end.")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping/ingest stage.")
    parser.add_argument("--overwrite-existing", action="store_true", help="Force LLM to overwrite existing labels.")
    parser.add_argument("--ready-output", default=str(DEFAULT_READY_OUT), help="Path to final linguistic_ready.jsonl")
    args = parser.parse_args()

    if not args.skip_scrape:
        _run(["python3", str(SCRAPE_SCRIPT), "--source", "all"])
    _run(["python3", str(FILTER_SCRIPT)])

    llm_cmd = ["python3", str(LABEL_SCRIPT)]
    if args.overwrite_existing:
        llm_cmd.append("--overwrite-existing")
    _run(llm_cmd)

    ready_output = Path(args.ready_output)
    ready_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DEFAULT_LABELED, ready_output)
    print(f"Ready file written: {ready_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
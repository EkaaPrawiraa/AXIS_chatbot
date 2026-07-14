"""Run and preserve the deterministic RM3 memory-contract evidence.

This is deliberately separate from LLM-as-judge evaluation.  The checks here
verify implementation contracts whose oracle is deterministic: graph writes,
lifecycle links, graph expansion, and user controls.  Semantic quality metrics
such as nDCG@5 or grounded-answer rate require a labelled corpus and remain in
their own evaluation block.

Run from the repository root after loading ``agentic/.env``:

    .venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_contract_eval.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / "docs/thesis_latex/evaluasi_v2/rm3_memori/lifecycle_contract_results.json"

GROUPS = {
    "memori_inti": [
        "agentic/tests/test_memory",
        "--ignore=agentic/tests/test_memory/test_user_control_contracts.py",
    ],
    "lifecycle_dan_konteks": [
        "agentic/tests/test_memory/test_belief_evolution.py",
        "agentic/tests/test_memory/test_graph_expansion.py",
        "agentic/tests/test_memory/test_kg_writer.py",
    ],
    "kendali_pengguna": ["agentic/tests/test_memory/test_user_control_contracts.py"],
    "confession_space": ["agentic/tests/test_feature_bot/test_session/test_confession_mode_persistence.py"],
}


def load_agentic_env() -> None:
    """Make database-backed contract runs reproducible from the repository root."""
    path = ROOT / "agentic" / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def run_group(name: str, targets: list[str]) -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", "-q", *targets]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    match = re.search(r"(\d+) passed(?:, (\d+) failed)?", output)
    skipped_match = re.search(r"(\d+) skipped", output)
    passed = int(match.group(1)) if match else 0
    failed = int(match.group(2) or 0) if match else 0
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    return {
        "group": name,
        "command": command,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "exit_code": completed.returncode,
        "output": output,
    }


def main() -> int:
    load_agentic_env()
    groups = [run_group(name, targets) for name, targets in GROUPS.items()]
    payload = {
        "evaluation": "RM3 deterministic lifecycle and control contracts",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "scope": (
            "Deterministic production-contract checks. This artifact is not an "
            "LLM-as-judge substitute for semantic retrieval or response quality."
        ),
        "groups": groups,
        "summary": {
            "passed": sum(int(group["passed"]) for group in groups),
            "failed": sum(int(group["failed"]) for group in groups),
            "all_groups_passed": all(
                int(group["exit_code"]) == 0 and int(group["skipped"]) == 0
                for group in groups
            ),
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    for group in groups:
        print(
            f"{group['group']}: {group['passed']} passed, "
            f"{group['failed']} failed, {group['skipped']} skipped"
        )
    return 0 if payload["summary"]["all_groups_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

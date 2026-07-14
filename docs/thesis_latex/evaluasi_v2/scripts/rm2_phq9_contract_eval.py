"""Run the PHQ-9 production-contract suite and retain its exact output."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / "docs/thesis_latex/evaluasi_v2/rm2_phq9/contract_test_results.json"
TARGETS = [
    "agentic/tests/test_assessment",
    "agentic/tests/test_feature_bot/test_assessment_bot",
]


def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q", *TARGETS]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}".strip()
    match = re.search(r"(\d+) passed(?:, (\d+) failed)?", output)
    passed = int(match.group(1)) if match else 0
    failed = int(match.group(2) or 0) if match else 0
    payload = {
        "evaluation": "RM2 PHQ-9 production-contract suite",
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "command": command,
        "passed": passed,
        "failed": failed,
        "exit_code": completed.returncode,
        "output": output,
        "scope": (
            "Offer timing, onboarding trigger, delivery, free-text scoring, "
            "clarification, scoring, feedback, and graph routing."
        ),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}: {passed} passed, {failed} failed")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

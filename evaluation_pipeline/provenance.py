"""Reproducibility manifest helpers."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from config import EvaluationConfig, REPO_ROOT
from scenarios import Scenario


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _package_versions(names: Iterable[str]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def build_manifest(
    *,
    run_id: str,
    config: EvaluationConfig,
    systems: list[str],
    scenarios: list[Scenario],
    repetitions: int,
    baseline_prompt: str,
) -> dict[str, Any]:
    status = _git("status", "--porcelain")
    scenario_payload = [scenario.snapshot() for scenario in scenarios]

    # Resolve the response_generator prompt actually in effect (v2 or v3,
    # via AXIS_RESPONSE_PIPELINE_VERSION) rather than hardcoding v2 -- a v3
    # run must not have its manifest silently claim v2's prompt file ran.
    agentic_path = str(REPO_ROOT / "agentic")
    if agentic_path not in sys.path:
        sys.path.insert(0, agentic_path)
    from agentic.config.llm_models import RESPONSE_GENERATOR

    response_generator_ref = RESPONSE_GENERATOR.resolved_prompt_ref

    prompt_paths = {
        "axis_identity": REPO_ROOT
        / "agentic/prompts/system/axis_identity.yaml",
        "axis_response_generator": REPO_ROOT
        / "agentic/prompts" / f"{response_generator_ref}.yaml",
        "axis_kg_extractor": REPO_ROOT
        / "agentic/prompts/nodes/kg_extractor.yaml",
    }
    return {
        "schema_version": 1,
        "run_id": run_id,
        "protocol": "scripted_paired_inputs",
        "systems": systems,
        "repetitions": repetitions,
        "config": config.public_snapshot(),
        "source": {
            "git_commit": _git("rev-parse", "HEAD"),
            "git_dirty": bool(status),
            "git_changed_paths": status.splitlines() if status else [],
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": _package_versions(
                (
                    "openai",
                    "psycopg2-binary",
                    "neo4j",
                    "langgraph",
                    "langchain-google-genai",
                    "google-genai",
                )
            ),
        },
        "scenarios": scenario_payload,
        "hashes": {
            "scenario_definition": sha256_text(
                json.dumps(scenario_payload, sort_keys=True, ensure_ascii=False)
            ),
            "baseline_system_prompt": sha256_text(baseline_prompt),
            **{
                name: sha256_file(path) for name, path in prompt_paths.items()
            },
        },
        "interpretation_notes": [
            "Provider model aliases may refer to mutable hosted models.",
            "Provider seed is sent only when EVAL_SEND_PROVIDER_SEED=1.",
            "AXIS-vs-baseline compares complete systems rather than isolated graph retrieval.",
        ],
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

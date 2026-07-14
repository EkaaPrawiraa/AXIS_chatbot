"""Judge the semantic adequacy of a real lifecycle probe with two LLM judges.

The probe is an earlier successful end-to-end session-finalizer run.  It
contains the user's two explicit reappraisals and the Neo4j lifecycle edges
observed after finalization.  This script does not expose model reasoning; it
stores only the rubric labels, model identities, and adjudicated result.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "evaluation_pipeline/results/reappraisal_probe.json"
OUTPUT = ROOT / "docs/thesis_latex/evaluasi_v2/rm3_memori/lifecycle_llm_judge_results.json"
JUDGES = ("gpt-4o-mini", "gpt-4.1-mini")
ADJUDICATOR = "gpt-4o-mini"

SESSION_2_TURNS = [
    "Saya dulu takut sidang tugas akhir akan gagal total. Setelah presentasi latihan di depan teman-teman berjalan cukup lancar dan mendapat masukan positif, saya menilai situasinya tidak seburuk bayangan awal.",
    "Saya dulu menganggap komentar ketus dosen pembimbing berarti beliau kecewa. Setelah dipikir ulang, saya menafsirkan komentar itu mungkin dipengaruhi beban kerja beliau, bukan kekecewaan pribadi.",
]


def load_env() -> None:
    for path in (ROOT / "agentic/.env", ROOT / "evaluation_pipeline/.env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def call_judge(client: OpenAI, model: str, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompt = f"""Anda adalah penilai buta untuk evaluasi lifecycle memori non-klinis.
Nilai apakah relasi memori yang diamati benar-benar merepresentasikan pemaknaan
ulang yang tersurat dalam cerita pengguna. Jangan menilai gaya bahasa atau
kualitas klinis. Untuk setiap kasus, keluarkan HANYA JSON object tanpa markdown
dengan bentuk berikut dan pertahankan seluruh id persis seperti masukan:
{{"results":[{{"id": string, "supports_reappraisal": true|false}}]}}

Cerita pengguna pada sesi kedua:
{json.dumps(SESSION_2_TURNS, ensure_ascii=False)}

Relasi yang diamati:
{json.dumps(cases, ensure_ascii=False)}
"""
    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0,
        text={"format": {"type": "json_object"}},
    )
    raw = response.output_text.strip()
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = parsed.get("results", parsed.get("cases", []))
    if not isinstance(parsed, list):
        raise ValueError(f"{model} did not return a JSON list")
    return [dict(item) for item in parsed]


def main() -> None:
    load_env()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is unavailable")
    if not SOURCE.exists():
        raise RuntimeError(f"Missing lifecycle probe artifact: {SOURCE}")

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for index, relation in enumerate(source.get("supersedes_relations", []), start=1):
        cases.append({
            "id": f"thought-{index}",
            "kind": "thought_supersession",
            "old_content": relation.get("old_content"),
            "new_content": relation.get("new_content"),
            "old_active": relation.get("old_active"),
            "reason": relation.get("reason"),
        })
    for index, relation in enumerate(source.get("reappraised_as_relations", []), start=1):
        cases.append({
            "id": f"experience-{index}",
            "kind": "experience_reappraisal",
            "old_content": relation.get("old_description"),
            "new_content": relation.get("new_description"),
            "old_active": relation.get("old_active"),
        })
    if not cases:
        raise RuntimeError("Lifecycle probe did not contain any observed relation")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    outputs = {model: call_judge(client, model, cases) for model in JUDGES}
    by_judge = {
        model: {str(row["id"]): row for row in rows}
        for model, rows in outputs.items()
    }
    first, second = JUDGES
    disagreements = [
        case["id"] for case in cases
        if by_judge[first].get(case["id"], {}).get("supports_reappraisal")
        != by_judge[second].get(case["id"], {}).get("supports_reappraisal")
    ]
    final = dict(by_judge[first])
    if disagreements:
        adjudicated = call_judge(client, ADJUDICATOR, [case for case in cases if case["id"] in disagreements])
        final.update({str(row["id"]): row for row in adjudicated})

    verdicts = [bool(final[case["id"]].get("supports_reappraisal")) for case in cases]
    old_thoughts_inactive = [
        bool(relation.get("old_active") is False)
        for relation in source.get("supersedes_relations", [])
    ]
    payload = {
        "source_artifact": str(SOURCE.relative_to(ROOT)),
        "judge_models": list(JUDGES),
        "adjudicator_model": ADJUDICATOR if disagreements else None,
        "n_cases": len(cases),
        "n_disagreements": len(disagreements),
        "cases": cases,
        "raw_judges": outputs,
        "final_labels": [final[case["id"]] for case in cases],
        "summary": {
            "semantic_lifecycle_match_rate": sum(verdicts) / len(verdicts),
            "semantic_lifecycle_matches": sum(verdicts),
            "old_superseded_thoughts_inactive_rate": (
                sum(old_thoughts_inactive) / len(old_thoughts_inactive)
                if old_thoughts_inactive else None
            ),
            "old_superseded_thoughts_inactive": sum(old_thoughts_inactive),
            "n_superseded_thoughts": len(old_thoughts_inactive),
        },
        "limit": (
            "This evaluates one successful end-to-end probe and does not estimate "
            "population-level update correctness or stale-memory rate."
        ),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

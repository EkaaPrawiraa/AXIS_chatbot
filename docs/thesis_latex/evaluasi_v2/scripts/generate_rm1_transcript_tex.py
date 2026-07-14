"""Render docs/thesis_latex/evaluasi_v2/rm1_dialogue/raw_results_expanded.json into a
LaTeX fragment with the real per-scenario transcript and judge scores, so the
appendix transcript can never drift from the actual saved evaluation artifact.

Run from repo root: .venv/bin/python3 docs/thesis_latex/evaluasi_v2/scripts/generate_rm1_transcript_tex.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVAL_DIR = ROOT / "docs" / "thesis_latex" / "evaluasi_v2"
OUT_PATH = ROOT / "docs" / "thesis_latex" / "chapters" / "generated_rm1_transcript.tex"

DIMENSION_LABELS = {
    "reaksi_emosional": "Reaksi emosional",
    "interpretasi_konteks": "Interpretasi konteks",
    "eksplorasi": "Eksplorasi",
    "ketepatan_cbt": "Ketepatan CBT",
    "batas_non_klinis": "Batas non-klinis",
    "kesesuaian_bahasa": "Kesesuaian bahasa",
    "groundedness": "Groundedness",
}

SCENARIO_TITLES = {
    "rm1_family": "Tekanan Keluarga (Arya, \\textit{cold start})",
    "rm1_organizational": "Beban Organisasi (Arya, \\textit{cold start})",
    "rm1_career": "Ketidakpastian Karier (Arya, \\textit{cold start})",
    "rm1_academic_memory_1": "Kelanjutan Tekanan Akademik (Budi, memori kaya) \\#1",
    "rm1_academic_memory_2": "Kelanjutan Tekanan Akademik (Budi, memori kaya) \\#2",
    "rm1_academic_memory_3": "Kelanjutan Tekanan Akademik (Budi, memori kaya) \\#3",
}

_LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def esc(text: str) -> str:
    return "".join(_LATEX_SPECIAL.get(ch, ch) for ch in text)


def main() -> None:
    data = json.loads((EVAL_DIR / "rm1_dialogue" / "raw_results_expanded.json").read_text(encoding="utf-8"))

    lines: list[str] = []
    for scenario in data:
        key = scenario["scenario"]
        title = SCENARIO_TITLES.get(key, esc(key))
        axis_is_a = scenario["axis_is_a"]

        lines.append(f"\\section{{{title}}}")
        lines.append("\\addcontentsline{loa}{lampiransub}{\\protect\\numberline{\\thesection}" + title + "}")
        lines.append("")
        lines.append(f"\\textbf{{Pesan pengguna:}} {esc(scenario['user_message'])}")
        lines.append("")
        lines.append(f"\\textbf{{Respons AXIS:}} {esc(scenario['axis_reply'])}")
        lines.append("")
        lines.append(f"\\textbf{{Respons \\textit{{baseline}}:}} {esc(scenario['baseline_reply'])}")
        lines.append("")

        lines.append("\\begin{table}[!htbp]")
        lines.append("\\centering")
        lines.append(f"\\caption{{Skor penilai dan preferensi -- {title}}}")
        lines.append("{\\footnotesize")
        lines.append(
            "\\begin{tabularx}{\\textwidth}{|>{\\raggedright\\arraybackslash}X|"
            ">{\\centering\\arraybackslash}p{2.6cm}|>{\\centering\\arraybackslash}p{1.5cm}|"
            ">{\\centering\\arraybackslash}p{1.5cm}|}"
        )
        lines.append("\\hline")
        lines.append("\\rowcolor{tableheadgray}")
        lines.append(
            "\\textbf{Dimensi} & \\textbf{Konfigurasi penilai} & "
            "\\textbf{Skor A} & \\textbf{Skor B} \\\\"
        )
        lines.append("\\hline")
        for judge_name, judge in scenario["judge_results"].items():
            for dim_key, dim_label in DIMENSION_LABELS.items():
                sa = judge["scores_a"].get(dim_key, "-")
                sb = judge["scores_b"].get(dim_key, "-")
                lines.append(f"{dim_label} & {esc(judge_name)} & {sa} & {sb} \\\\")
            lines.append("\\hline")
        lines.append("\\end{tabularx}")
        lines.append("}")
        lines.append("\\end{table}")
        lines.append("")

        axis_label = "A" if axis_is_a else "B"
        for judge_name, judge in scenario["judge_results"].items():
            pref = judge["preference"]
            winner = (
                "AXIS" if pref == axis_label
                else ("Baseline" if pref in ("A", "B") else "Setara")
            )
            lines.append(
                f"\\textit{{{esc(judge_name)}}}: preferensi {pref} ({winner}). "
                f"Alasan: {esc(judge['reason'])}"
                "\\newline"
            )
        lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    main()

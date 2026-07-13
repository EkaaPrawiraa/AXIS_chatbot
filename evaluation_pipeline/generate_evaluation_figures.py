"""Generate the RM1-RM3 result figures used in BAB IV / Lampiran from the real
artifacts saved under docs/thesis_latex/evaluasi_v2/, so the figures can be
regenerated any time the underlying evaluation is re-run.

Run from repo root: cd agentic && ../.venv/bin/python -m evaluation_pipeline.generate_evaluation_figures
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "docs" / "thesis_latex" / "evaluasi_v2"
FIG_DIR = ROOT / "docs" / "thesis_latex" / "figures"

plt.rcParams.update({
    "font.size": 10,
    "axes.edgecolor": "#111111",
    "axes.labelcolor": "#111111",
    "text.color": "#111111",
    "xtick.color": "#111111",
    "ytick.color": "#111111",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

GRAY_AXIS = "#333333"
GRAY_BASELINE = "#aaaaaa"

DIMENSION_LABELS = {
    "reaksi_emosional": "Reaksi\nemosional",
    "interpretasi_konteks": "Interpretasi\nkonteks",
    "eksplorasi": "Eksplorasi",
    "ketepatan_cbt": "Ketepatan\nCBT",
    "batas_non_klinis": "Batas\nnon-klinis",
    "kesesuaian_bahasa": "Kesesuaian\nbahasa",
    "groundedness": "Groundedness\nmemori",
}


def plot_rm1_dialogue() -> None:
    data = json.loads((EVAL_DIR / "rm1_dialogue" / "raw_results.json").read_text(encoding="utf-8"))

    dims = list(DIMENSION_LABELS.keys())
    axis_scores: dict[str, list[float]] = {d: [] for d in dims}
    baseline_scores: dict[str, list[float]] = {d: [] for d in dims}

    for scenario in data:
        axis_is_a = scenario["axis_is_a"]
        for judge in scenario["judge_results"].values():
            scores_axis = judge["scores_a"] if axis_is_a else judge["scores_b"]
            scores_base = judge["scores_b"] if axis_is_a else judge["scores_a"]
            for d in dims:
                if d in scores_axis:
                    axis_scores[d].append(scores_axis[d])
                if d in scores_base:
                    baseline_scores[d].append(scores_base[d])

    axis_medians = [statistics.median(axis_scores[d]) for d in dims]
    baseline_medians = [statistics.median(baseline_scores[d]) for d in dims]

    x = range(len(dims))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar([i - width / 2 for i in x], axis_medians, width, label="AXIS", color=GRAY_AXIS)
    ax.bar([i + width / 2 for i in x], baseline_medians, width, label="Baseline", color=GRAY_BASELINE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([DIMENSION_LABELS[d] for d in dims], fontsize=8)
    ax.set_ylabel("Median skor rubrik (0-2)")
    ax.set_ylim(0, 2.3)
    ax.set_title("RM1a: Median skor rubrik per dimensi, AXIS vs baseline")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm1_dialogue_scores.pdf")
    plt.close(fig)


def plot_rm1_safety() -> None:
    data = json.loads((EVAL_DIR / "rm1_safety" / "results.json").read_text(encoding="utf-8"))
    m = data["metrics"]

    labels = ["Sensitivitas", "Spesifisitas", "Presisi", "F2"]
    values = [m["sensitivity"], m["specificity"], m["precision"], m["f2"]]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    bars = ax.bar(labels, values, color=GRAY_AXIS, width=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Nilai metrik")
    ax.set_title("RM1b: Benchmark keselamatan\n(eufemisme krisis vs benign)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm1_safety_metrics.pdf")
    plt.close(fig)


def plot_rm2_phq9() -> None:
    metrics = json.loads((EVAL_DIR / "rm2_phq9" / "metrics.json").read_text(encoding="utf-8"))

    labels = ["QWK", "Macro-F1", "Akurasi\n(skor numerik)", "Akurasi\nklarifikasi"]
    values = [
        metrics["quadratic_weighted_kappa"],
        metrics["macro_f1"],
        metrics["accuracy_numeric"],
        metrics["clarification_accuracy"],
    ]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    bars = ax.bar(labels, values, color=GRAY_AXIS, width=0.5)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Nilai metrik")
    ax.set_title("RM2: Pemetaan jawaban bebas PHQ-9 ke skor")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm2_phq9_metrics.pdf")
    plt.close(fig)


def plot_rm3_ablation() -> None:
    cond_a = json.loads((EVAL_DIR / "rm3_memori" / "recall_probe_condition_A_hybrid.json").read_text(encoding="utf-8"))
    cond_b = json.loads((EVAL_DIR / "rm3_memori" / "recall_probe_condition_B1_vector_only.json").read_text(encoding="utf-8"))

    recall_vector = cond_b["recall"]
    recall_hybrid = cond_a["recall"]

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))

    ax0 = axes[0]
    bars = ax0.bar(["Vektor saja", "Hibrid"], [recall_vector, recall_hybrid],
                    color=[GRAY_BASELINE, GRAY_AXIS], width=0.5)
    for bar, v in zip(bars, [recall_vector, recall_hybrid]):
        ax0.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax0.set_ylim(0, 1.15)
    ax0.set_ylabel("Recall@5")
    ax0.set_title("15 kueri parafrase\nsatu-hop")

    ax1 = axes[1]
    bars = ax1.bar(["Vektor saja", "Hibrid"], [0, 1], color=[GRAY_BASELINE, GRAY_AXIS], width=0.5)
    for bar, v, label in zip(bars, [0, 1], ["0/1", "1/1"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, v + 0.03, label, ha="center", fontsize=9)
    ax1.set_ylim(0, 1.15)
    ax1.set_ylabel("Berhasil menjawab kueri (0 atau 1)")
    ax1.set_title("Kasus bertarget: kueri\nberbagi entitas Trigger")

    fig.suptitle("RM3: Ablasi vektor saja vs hibrid")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm3_ablation_recall.pdf")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_rm1_dialogue()
    plot_rm1_safety()
    plot_rm2_phq9()
    plot_rm3_ablation()
    print("Saved: rm1_dialogue_scores.pdf, rm1_safety_metrics.pdf, rm2_phq9_metrics.pdf, rm3_ablation_recall.pdf")


if __name__ == "__main__":
    main()

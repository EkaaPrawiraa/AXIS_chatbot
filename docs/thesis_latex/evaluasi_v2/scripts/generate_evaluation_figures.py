"""Generate the RM1-RM3 result figures used in BAB IV / Lampiran from the real
artifacts saved under docs/thesis_latex/evaluasi_v2/, so the figures can be
regenerated any time the underlying evaluation is re-run.

Run from repo root: .venv/bin/python3 docs/thesis_latex/evaluasi_v2/scripts/generate_evaluation_figures.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[4]
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
    v3_path = ROOT / "docs" / "thesis_latex" / "evaluasi_v3" / "rm1_language" / "raw_results_v3.json"
    v2_path = EVAL_DIR / "rm1_dialogue" / "raw_results_expanded.json"
    data = json.loads((v3_path if v3_path.exists() else v2_path).read_text(encoding="utf-8"))
    primary_model = "gemini-3.1-flash-lite"

    dims = list(DIMENSION_LABELS.keys())
    axis_scores: dict[str, list[float]] = {d: [] for d in dims}
    baseline_scores: dict[str, list[float]] = {d: [] for d in dims}

    for scenario in data:
        axis_is_a = scenario["axis_is_a"]
        judge = scenario["judge_results"].get(primary_model)
        if not judge:
            continue
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
    data = json.loads((EVAL_DIR / "rm1_safety" / "llm_judge_results.json").read_text(encoding="utf-8"))
    m = data["summary"]["aggregate"]

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
    metrics = json.loads((EVAL_DIR / "rm2_phq9" / "llm_judge_extended_metrics.json").read_text(encoding="utf-8"))

    labels = ["QWK", "Macro-F1", "Akurasi\n(skor numerik)", "Akurasi\nklarifikasi"]
    values = [
        metrics["quadratic_weighted_kappa_numeric_output"],
        metrics["macro_f1_numeric_output"],
        metrics["exact_agreement_numeric"],
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


def plot_kappa_comparison() -> None:
    agreement = json.loads((EVAL_DIR / "judge_agreement.json").read_text(encoding="utf-8"))

    bars = [
        ("RM1b\nrisiko tinggi", agreement["rm1_safety"]["risk_cohen_kappa"]),
        ("RM1b\nragam bahasa", agreement["rm1_safety"]["language_slice_cohen_kappa"]),
        ("RM1b\nrespons aman", agreement["rm1_safety"]["response_all_compliant_cohen_kappa"]),
        ("RM2\nfrekuensi PHQ-9", agreement["rm2_phq9"]["frequency_quadratic_weighted_kappa"]),
        ("RM3\nlifecycle", agreement["rm3_lifecycle"]["semantic_lifecycle_match_cohen_kappa"]),
        ("RM1a/RM1c\npreferensi dialog", agreement["rm1_dialogue"]["preference_cohen_kappa"]),
    ]
    labels = [b[0] for b in bars]
    values = [b[1] for b in bars]
    colors = [GRAY_BASELINE if v < 0 else GRAY_AXIS for v in values]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_objs = ax.bar(labels, values, color=colors, width=0.55)
    for bar, v in zip(bar_objs, values):
        y = v + 0.03 if v >= 0 else v - 0.08
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{v:.2f}", ha="center", fontsize=9)
    ax.axhline(0, color="#111111", linewidth=0.8)
    ax.set_ylim(-0.15, 1.1)
    ax.set_ylabel("Cohen's kappa / QWK")
    ax.set_title("Kesepakatan dua konfigurasi penilai independen\nper blok evaluasi")
    ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "judge_kappa_comparison.pdf")
    plt.close(fig)


def plot_rm1c_language_preference() -> None:
    summary = json.loads(
        (ROOT / "docs" / "thesis_latex" / "evaluasi_v3" / "rm1_language" / "summary_v3.json").read_text(encoding="utf-8")
    )
    by_slice = summary["preference_by_language_slice"]
    order = ["formal", "informal", "code_mixing", "euphemistic"]
    slice_labels = {"formal": "Formal", "informal": "Informal", "code_mixing": "Bahasa\ncampur", "euphemistic": "Eufemistik"}

    labels = [slice_labels[s] for s in order]
    axis_counts = [by_slice[s]["axis"] for s in order]
    baseline_counts = [by_slice[s]["baseline"] for s in order]

    x = range(len(order))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.bar([i - width / 2 for i in x], axis_counts, width, label="AXIS", color=GRAY_AXIS)
    ax.bar([i + width / 2 for i in x], baseline_counts, width, label="Baseline", color=GRAY_BASELINE)
    for i, (a, b) in enumerate(zip(axis_counts, baseline_counts)):
        ax.text(i - width / 2, a + 0.1, str(a), ha="center", fontsize=9)
        ax.text(i + width / 2, b + 0.1, str(b), ha="center", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Jumlah skenario dipilih")
    ax.set_title("RM1c: Preferensi berpasangan per ragam bahasa\n(24 skenario, konfigurasi penilai primer)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm1c_language_preference.pdf")
    plt.close(fig)


def plot_rm3_scenario_metrics() -> None:
    writing = json.loads(
        (EVAL_DIR / "rm3_memori" / "node_writing_and_update_results.json").read_text(encoding="utf-8")
    )["summary"]
    usage = json.loads(
        (ROOT / "docs" / "thesis_latex" / "evaluasi_v3" / "rm3_usage" / "usage_grounding_results.json").read_text(encoding="utf-8")
    )["summary"]

    labels = [
        "Presisi\npenulisan",
        "Recall\npenulisan",
        "Macro-F1\npenulisan",
        "Update\ncorrectness",
        "Grounded-\nanswer rate",
        "False-\npersonalization\nrate",
        "Stale-belief\nrate",
    ]
    values = [
        writing["node_relation_writing"]["precision"],
        writing["node_relation_writing"]["recall"],
        writing["node_relation_writing"]["f1"],
        writing["update_correctness"]["update_correctness"],
        usage["dialogue_derived_rates"]["grounded_answer_rate"],
        usage["dialogue_derived_rates"]["false_personalization_rate"],
        usage["reappraisal_stale_belief"]["stale_belief_rate"],
    ]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(labels, values, color=GRAY_AXIS, width=0.55)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Nilai metrik")
    ax.set_title("RM3: Metrik skenario-dan-hasil penulisan,\npembaruan, dan penggunaan memori")
    ax.tick_params(axis="x", labelsize=7.5)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "rm3_scenario_metrics.pdf")
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plot_rm1_dialogue()
    plot_rm1_safety()
    plot_rm2_phq9()
    plot_rm3_ablation()
    plot_kappa_comparison()
    plot_rm1c_language_preference()
    plot_rm3_scenario_metrics()
    print(
        "Saved: rm1_dialogue_scores.pdf, rm1_safety_metrics.pdf, rm2_phq9_metrics.pdf, "
        "rm3_ablation_recall.pdf, judge_kappa_comparison.pdf, rm1c_language_preference.pdf, "
        "rm3_scenario_metrics.pdf"
    )


if __name__ == "__main__":
    main()

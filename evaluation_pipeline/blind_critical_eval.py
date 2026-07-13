"""Independent blind critical evaluation of the four comparative transcripts
(baseline/AXIS x Arya/Budi), run as a single isolated LLM call with no prior
conversation history and no access to this report's own conclusions, matching
the methodology described in Lampiran G (Evaluasi Kritis Independen).

Run from repo root: cd evaluation_pipeline && ../.venv/bin/python blind_critical_eval.py
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "agentic" / ".env")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
JUDGE_MODEL = "gpt-4o"

SYSTEM_DESCRIPTION = """\
AXIS adalah chatbot pendamping (companionship chatbot) non-klinis untuk mahasiswa \
Indonesia, dibangun sebagai tugas akhir. AXIS memiliki memori jangka panjang \
berbasis knowledge graph, kebijakan dialog yang dapat menawarkan teknik CBT \
(seperti grounding sensorik dan validasi emosi) ketika sinyal percakapan \
mendukung, serta guardrail keselamatan. Baseline adalah chatbot pembanding \
yang hanya melakukan pencarian kemiripan semantik (vector RAG) tanpa \
penalaran graf, tanpa kebijakan dialog CBT, dan tanpa guardrail berlapis.
"""

PROMPT_TEMPLATE = """\
Anda adalah evaluator kritis independen untuk empat transkrip wawancara chatbot \
pendamping. Tugas Anda adalah membaca keempat transkrip berikut dengan sangat \
skeptis, mencari kelemahan, pola artifisial, atau klaim yang berlebihan pada \
KEDUA sistem (baseline maupun AXIS), bukan hanya mencari bukti yang \
menguntungkan salah satu sistem.

Deskripsi sistem:
{system_description}

=== TRANSKRIP 1: Persona Arya, Baseline ===
{arya_baseline}

=== TRANSKRIP 2: Persona Arya, AXIS ===
{arya_axis}

=== TRANSKRIP 3: Persona Budi, Baseline ===
{budi_baseline}

=== TRANSKRIP 4: Persona Budi, AXIS ===
{budi_axis}

Tuliskan evaluasi kritis Anda dalam bahasa Indonesia, terstruktur sebagai \
beberapa temuan bernomor, masing-masing dengan judul singkat tebal dan \
penjelasan 2-4 kalimat yang merujuk kutipan atau giliran spesifik dari \
transkrip di atas. Tutup dengan satu paragraf verdict keseluruhan yang \
membandingkan kedua sistem secara jujur, termasuk menyebutkan perbaikan \
tunggal yang menurut Anda paling berdampak. Jangan gunakan tanda baca titik \
koma atau em dash, gunakan kalimat naratif biasa.
"""


def main() -> None:
    results_dir = ROOT / "evaluation_pipeline" / "results"
    arya_baseline = (results_dir / "chatbot_x_arya.md").read_text(encoding="utf-8")
    arya_axis = (results_dir / "axis_arya.md").read_text(encoding="utf-8")
    budi_baseline = (results_dir / "chatbot_x_budi.md").read_text(encoding="utf-8")
    budi_axis = (results_dir / "axis_budi.md").read_text(encoding="utf-8")

    prompt = PROMPT_TEMPLATE.format(
        system_description=SYSTEM_DESCRIPTION,
        arya_baseline=arya_baseline,
        arya_axis=arya_axis,
        budi_baseline=budi_baseline,
        budi_axis=budi_axis,
    )

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    text = response.choices[0].message.content

    out_path = results_dir / "blind_critical_eval.md"
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

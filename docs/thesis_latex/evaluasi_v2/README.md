# Artefak Evaluasi Bab IV

Folder ini menyimpan artefak yang menjadi sumber angka pada Bab IV naskah
`seminar_hasil_v2.tex`.

- `rm1_dialogue/`: penilaian buta respons suportif.
- `rm1_safety/`: benchmark deteksi risiko dan kepatuhan respons pascadeteksi.
- `rm2_phq9/`: orkestrasi, pemetaan jawaban bebas, klarifikasi, serta rute item
  kesembilan.
- `rm3_memori/`: probe pengambilan memori hibrid dan vektor-saja.
- `scripts/`: skrip reproduksi dan generator gambar.

## Menjalankan ulang

Jalankan dari akar repositori setelah layanan lokal dan variabel lingkungan
agentik tersedia:

```bash
set -a; source agentic/.env; set +a
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm1_safety_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/summarize_judge_agreement.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/generate_evaluation_figures.py
```

RM3 melaporkan kontrak lifecycle deterministik dan satu probe reappraisal
end-to-end yang dinilai LLM, di samping probe pengambilan memori. Korpus
relevansi berjenjang untuk P@5, MRR, nDCG@5, dan korpus kualitas jawaban belum
tersedia; angka untuk metrik tersebut tidak diisi pada Bab IV.

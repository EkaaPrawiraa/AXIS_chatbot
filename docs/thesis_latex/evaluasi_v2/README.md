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
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm1_dialogue_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_longmemeval_retrieval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/generate_evaluation_figures.py
```

RM3 melaporkan kontrak lifecycle deterministik, satu probe reappraisal
end-to-end yang dinilai LLM, probe pengambilan memori internal, serta kalibrasi
retrieval sesi pada sampel LongMemEval_S. Korpus eksternal tersebut menyediakan
label sesi bukti untuk P@5, Recall@5, MRR, dan nDCG@5, tetapi bukan anotasi graf
AXIS atau pasangan jawaban berlabel. Karena itu, metrik kualitas penggunaan
memori pada jawaban tetap belum diisi.

Seluruh skrip penilaian dan pembangkitan teks LLM yang aktif memakai
`gemini-3.1-flash-lite`. Pada penilaian dialog, model yang sama juga dipakai
untuk pembangkitan AXIS dan baseline hanya selama proses evaluasi; konfigurasi
deployment tidak berubah. Kalibrasi retrieval tetap memakai model *embedding*
tersendiri karena tugasnya membentuk vektor, bukan menyusun atau menilai teks.

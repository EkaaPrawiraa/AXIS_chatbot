# Artefak Evaluasi Bab IV

Folder ini menyimpan artefak yang menjadi sumber angka pada Bab IV naskah
`seminar_hasil_v2.tex`.

- `rm1_dialogue/`: penilaian buta respons suportif.
- `rm1_safety/`: benchmark deteksi risiko dan kepatuhan respons pascadeteksi.
- `rm2_phq9/`: orkestrasi, pemetaan jawaban bebas, klarifikasi, serta rute item
  kesembilan.
- `rm3_memori/`: penulisan node, *update correctness*, probe pengambilan
  memori hibrid dan vektor-saja, serta kalibrasi retrieval eksternal.
- `scripts/`: skrip reproduksi dan generator gambar.
- `judge_agreement.json`: ringkasan kesepakatan (Cohen's kappa/QWK) antara dua
  konfigurasi penilai independen, dihasilkan oleh
  `scripts/summarize_judge_agreement.py`.

## Menjalankan ulang

Jalankan dari akar repositori setelah layanan lokal dan variabel lingkungan
agentik tersedia:

```bash
set -a; source agentic/.env; set +a
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm1_safety_benchmark.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm1_safety_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm1_dialogue_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_mapping.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm2_phq9_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_contract_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_lifecycle_llm_judge.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_node_writing_and_update_eval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_longmemeval_retrieval.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/retrieval_recall_probe.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/rm3_bootstrap_ci.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/summarize_judge_agreement.py
.venv/bin/python docs/thesis_latex/evaluasi_v2/scripts/generate_evaluation_figures.py
```

RM3 melaporkan kontrak lifecycle deterministik, penulisan node dan *update
correctness* melalui pengujian skenario-dan-hasil (tidak ada korpus publik
berbahasa Indonesia yang sesuai untuk kemampuan ini), satu probe reappraisal
end-to-end yang dinilai dua konfigurasi penilai, probe pengambilan memori
internal, serta kalibrasi retrieval sesi pada sampel LongMemEval_S. Korpus
eksternal tersebut menyediakan label sesi bukti untuk P@5, Recall@5, MRR, dan
nDCG@5, tetapi bukan anotasi graf AXIS atau pasangan jawaban berlabel. Karena
itu, metrik kualitas penggunaan memori pada jawaban (*grounded-answer rate*
dan sejenisnya) tetap belum diisi.

Konfigurasi penilai primer pada seluruh skrip adalah `gemini-3.1-flash-lite`.
Untuk benchmark keselamatan (RM1b), pemetaan jawaban bebas PHQ-9 (RM2), dan
probe pemaknaan ulang memori (RM3), konfigurasi kedua yang independen
(`gemini-3.1-pro-preview`) melabeli ulang korpus yang sama secara buta;
kesepakatannya direkam pada `judge_agreement.json`. Penilaian dialog (RM1a)
masih memakai satu konfigurasi. Pada penilaian dialog, model penilai primer
juga dipakai untuk pembangkitan AXIS dan baseline hanya selama proses
evaluasi; konfigurasi deployment tidak berubah. Kalibrasi retrieval tetap
memakai model *embedding* tersendiri karena tugasnya membentuk vektor, bukan
menyusun atau menilai teks.

# Figure Source Manifest

Folder ini menyimpan file sumber gambar yang dapat diedit. Output final tetap
berada di `docs/thesis_latex/figures/` agar referensi LaTeX tidak berubah.

## Prinsip Visual

- Diagram laporan memakai gaya formal: hitam, putih, dan abu-abu.
- Use case diagram memakai aktor, batas sistem, dan use case.
- Flowchart memakai terminator, proses, keputusan, dan panah arah alur.
- Sequence diagram memakai aktor/partisipan, lifeline, dan message.
- Screenshot aplikasi tetap dipertahankan sebagai bukti implementasi, sehingga
  tidak dipaksa menjadi grayscale.

## Struktur

- `drawio/`: sumber Draw.io (`.drawio`) untuk pengeditan manual.
- `mermaid/`: sumber Mermaid (`.mmd`) untuk ekspor cepat ke PDF/PNG.
- `dot/`: folder legacy Graphviz. Saat ini kosong karena diagram yang dipakai
  laporan sudah dipindahkan ke Mermaid atau Draw.io.

## Mermaid

Semua Mermaid memakai `mermaid/formal-theme.json` agar konsisten secara visual.
Output yang dipakai LaTeX berada di `../<nama>.pdf`. Pratinjau PNG dapat
dihasilkan saat diperlukan, tetapi tidak disimpan sebagai artefak tetap agar
folder gambar hanya berisi keluaran yang benar-benar dipakai laporan.
Diagram konseptual yang perlu ditata secara manual memakai Draw.io sebagai
sumber ekspor aktif. Mermaid dipakai untuk diagram teknis yang lebih mudah
dipelihara sebagai kode.

Daftar sumber Mermaid yang aktif:

- `langgraph_flow.mmd` -> `../langgraph_flow.pdf`
- `seq_chat_turn.mmd` -> `../seq_chat_turn.pdf`
- `kg_schema.mmd` -> `../kg_schema.pdf`
- `seq_session_finalize.mmd` -> `../seq_session_finalize.pdf`
- `kg_lifecycle.mmd` -> `../kg_lifecycle.pdf`
- `context_builder_ranking.mmd` -> `../context_builder_ranking.pdf`
- `crisis_tier_flow.mmd` -> `../crisis_tier_flow.pdf`

Contoh ekspor:

```bash
mmdc -i src/mermaid/solution_use_case.mmd \
  -o solution_use_case.pdf \
  -b white \
  --pdfFit \
  -c src/mermaid/formal-theme.json
```

Untuk mengekspor seluruh Mermaid:

```bash
for f in src/mermaid/*.mmd; do
  name=$(basename "$f" .mmd)
  mmdc -i "$f" -o "../${name}.pdf" -b white --pdfFit -c src/mermaid/formal-theme.json
done
```

## Draw.io

File Draw.io dipertahankan sebagai sumber manual untuk diagram yang ingin
diubah melalui editor visual. `axis_conceptual_diagrams.drawio` adalah sumber
aktif untuk diagram konseptual berikut:

- halaman 1 -> `../solution_use_case.pdf`;
- halaman 2 -> `../solution_overview_flow.pdf`;
- halaman 3 -> `../cbt_dialogue_flow.pdf`;
- halaman 4 -> `../phq9_concept_flow.pdf`;
- halaman 5 -> `../memory_concept_flow.pdf`;
- halaman 6 -> `../guardrail_concept_flow.pdf`;
- halaman 7 -> `../evaluation_three_tracks.pdf`; dan
- halaman 8 -> `../seq_memory_concept.pdf`.

`phq9_state_machine.drawio` adalah sumber aktif untuk
`../phq9_state_machine.pdf`. Diagram ini memakai notasi flowchart formal:
terminator untuk awal/akhir giliran, persegi panjang untuk proses, dan belah
ketupat untuk keputusan, sehingga jalur penawaran, pengisian, serta eskalasi
dapat dibaca tanpa garis balik yang menutupi label.

Untuk naskah potret, keluaran tersebut dipotong menjadi dua artefak turunan:
`../phq9_state_machine_offer.pdf` dan
`../phq9_state_machine_completion.pdf`. Keduanya menampilkan fase penawaran
serta fase pengisian/penyelesaian pada halaman terpisah, tanpa mengubah sumber
Draw.io. Jika sumber diekspor ulang, perbarui kedua potongan tersebut sebelum
kompilasi LaTeX.

`system_architecture.drawio` adalah sumber aktif untuk
`../system_architecture.pdf` agar lapisan layanan dan tanggung jawab
penyimpanannya dapat ditata vertikal tanpa garis yang saling menimpa.

- `axis_conceptual_diagrams.drawio`
- `phq9_state_machine.drawio`
- `system_architecture.drawio`

Jika sebuah gambar Draw.io diekspor ulang, pastikan output akhir tetap berada di
`docs/thesis_latex/figures/` dengan nama file yang sama seperti referensi LaTeX.

```bash
cd docs/thesis_latex/figures

find . -type f -iname '*.png' -print0 |
while IFS= read -r -d '' png; do
  img2pdf "$png" -o "${png%.*}.pdf"
done
```

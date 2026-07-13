# Thesis LaTeX

Sumber LaTeX laporan Tugas Akhir.

**Judul:** Pengembangan Empathic Voice First Companionship Chatbot dengan Memory Based Personalization melalui Knowledge Graph untuk Mahasiswa
**Penulis:** Mohammad Nugraha Eka Prawira (NIM 13522001)
**Pembimbing:** Dr. Agung Dewandaru, S.T., M.Sc.
**Program Studi:** Teknik Informatika, STEI, ITB

## Struktur folder

```
thesis_latex/
├── main.tex                       # Root document
├── preamble.tex                   # Package dan konfigurasi
├── chapters/
│   ├── bab1.tex                   # Pendahuluan
│   ├── bab2.tex                   # Kajian Pustaka
│   ├── bab3.tex                   # Deskripsi Solusi (placeholder)
│   ├── bab4.tex                   # Evaluasi (placeholder)
│   └── bab5.tex                   # Kesimpulan dan Saran (placeholder)
├── frontmatter/
│   ├── cover.tex                  # Halaman sampul
│   ├── approval.tex               # Halaman pengesahan
│   ├── declaration.tex            # Lembar pernyataan
│   ├── abstract.tex               # Abstrak Bahasa Indonesia
│   ├── abstract_en.tex            # Abstract English
│   └── preface.tex                # Kata pengantar
├── bibliography/
│   └── references.bib             # Database referensi BibTeX
├── figures/                       # Gambar (PDF/PNG)
└── README.md
```

## Build

Memerlukan TeX Live atau MiKTeX dengan biblatex backend bibtex.

```bash
# Manual build (3 pass untuk citation + cross-ref)
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Atau dengan latexmk (rekomendasi):

```bash
latexmk -pdf -bibtex main.tex
```

Untuk clean intermediate files:

```bash
latexmk -c
```

## Konvensi

- Citation menggunakan biblatex APA style dengan backend bibtex.
- `\textcite{key}` untuk in-text citation (misal "Astutik et al. (2020) menunjukkan...").
- `\parencite{key}` untuk parenthetical citation (misal "...(Astutik et al., 2020).").
- Tidak menggunakan em dash. Gunakan tanda kurung biasa atau frasa pengganti.
- Heading angka Roman untuk chapter (I, II, III, IV, V), Arabic untuk section.
- Margins: top 2.5 cm, bottom 2.5 cm, left 3 cm, right 2.5 cm (Pedoman ITB).
- Font Times New Roman 12pt body, line spacing 1.5.

## Status BAB

| BAB | Judul | Status |
|-----|-------|--------|
| I | Pendahuluan | Draft v4 (final) |
| II | Kajian Pustaka | Draft v7 (final, mencakup subbab Persona AXIS) |
| III | Deskripsi Solusi | Placeholder |
| IV | Evaluasi | Placeholder |
| V | Kesimpulan dan Saran | Placeholder |

## Catatan rancangan penting

1. **Framing evaluasi**: BAB 1 dan BAB 4 menggunakan framing positive (technical validation yang dapat direplikasi). Studi yang melibatkan partisipan dan persetujuan etik diposisikan sebagai roadmap di BAB V.

2. **Hybrid retrieval**: Klaim hybrid di subbab II.5.7 secara eksplisit dispesifikkan sebagai hybrid by composition (lima sinyal terpisah yang dilampirkan ke konteks), bukan fusion ranking (RRF, MMR). Ekstensi ke unified fusion ranking dijabarkan sebagai roadmap.

3. **Latensi**: Strategi C dengan reframe trade-off deliberate. Sistem menyediakan dua mode operasi (normal vs streaming) dan dua tier model (cepat-singkat vs lebih bermakna). Diakui di subbab II.4.2.

4. **Persona AXIS**: Justifikasi di subbab II.2.3. Disiplin stabilitas lintas sesi diakui sebagai kontrak rancangan.

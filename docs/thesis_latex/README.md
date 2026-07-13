# Thesis LaTeX

Sumber LaTeX laporan Tugas Akhir.

**Judul resmi:** Pengembangan *Companionship Chatbot* dengan Asesmen Depresi melalui Percakapan dan Memori Jangka Panjang Berbasis *Knowledge Graph* untuk Mahasiswa Indonesia
**Penulis:** Mohammad Nugraha Eka Prawira (NIM 13522001)
**Pembimbing:** Dr. Agung Dewandaru, S.T., M.Sc.
**Program Studi:** Teknik Informatika, STEI, ITB

## Struktur folder

```
thesis_latex/
├── main.tex                       # Root laporan lengkap; memakai naskah V2 dan menambahkan Bab V
├── seminar_hasil_v2.tex           # Naskah seminar hasil utama
├── preamble.tex                   # Package dan konfigurasi
├── chapters/
│   ├── bab1.tex                   # Pendahuluan
│   ├── bab2.tex                   # Kajian Pustaka
│   ├── bab3.tex                   # Deskripsi solusi konseptual
│   ├── bab4.tex                   # Implementasi dan evaluasi utama
│   ├── bab4_evaluasi_v2.tex       # Protokol dan pelaporan evaluasi v2
│   ├── lampiran.tex               # Lampiran teknis dan visual aktif
│   ├── lampiran_evaluasi_v2.tex   # Instrumen evaluasi aktif
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

## Traceability Naskah

`seminar_hasil_v2.tex` adalah naskah utama untuk seminar hasil. `main.tex` memakai Bab IV dan lampiran V2 yang sama, lalu menambahkan Bab V untuk laporan lengkap. Berkas pembungkus dan naskah seminar lama sudah dibersihkan agar hanya ada satu jalur sumber aktif.

Judul resmi diturunkan ke tiga rumusan masalah sebagai berikut.

| Rumusan masalah | Dasar kajian (Bab II) | Keputusan solusi (Bab III) | Implementasi dan bukti (Bab IV) |
|---|---|---|---|
| RM1: percakapan pendamping | Empati, CBT, ragam bahasa mahasiswa, dan batas keselamatan | Persona, percakapan reflektif, serta batas keselamatan | Alur percakapan, kebijakan CBT, dan validasi komponen kritis |
| RM2: mood dan asesmen skrining depresi | Mood sebagai konteks harian, PHQ-9, penyampaian percakapan, dan JITAI | Mood harian serta PHQ-9 sukarela dan adaptif | Implementasi orkestrasi dan validasi transisi; korpus jawaban bebas masih direncanakan |
| RM3: memori jangka panjang berbasis graf | Memori personal, konteks permasalahan mahasiswa, representasi relasional, pemeringkatan, dan siklus hidup | Penulisan, penghubungan, pembaruan, serta pemanfaatan konteks permasalahan yang relevan | Arsitektur hibrid, kalibrasi domain finalizer, siklus hidup memori, dan rancangan benchmark berlabel |

Istilah ``asesmen depresi'' pada naskah ini selalu merujuk pada skrining PHQ-9. Istilah tersebut tidak berarti diagnosis maupun klaim efektivitas klinis.

Status evaluasi saat ini: validasi fungsional tersedia. Benchmark berlabel dan pengujian pengguna nyata masih merupakan evaluasi lanjutan; hasilnya tidak ditulis sebagai temuan yang telah diperoleh.

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

Untuk membangun naskah seminar hasil utama:

```bash
latexmk -pdf -bibtex seminar_hasil_v2.tex
```

Untuk clean intermediate files:

```bash
latexmk -c
```

## Konvensi

- Sitasi menggunakan `natbib` dengan gaya daftar pustaka ITB (`itbnat`).
- `\textcite{key}` untuk in-text citation (misal "Astutik et al. (2020) menunjukkan...").
- `\parencite{key}` untuk parenthetical citation (misal "...(Astutik et al., 2020).").
- Tidak menggunakan em dash. Gunakan tanda kurung biasa atau frasa pengganti.
- Heading angka Roman untuk chapter (I, II, III, IV, V), Arabic untuk section.
- Margin: atas 3 cm, bawah 3 cm, kiri 4 cm, kanan 3 cm.
- Font Times New Roman 12pt body, line spacing 1.5.
- Artefak lampiran yang berupa gambar dan tabel memakai nomor serta caption otomatis. Karena itu, artefak tersebut dapat dirujuk dan muncul pada Daftar Gambar atau Daftar Tabel.

## Status BAB

| BAB | Judul | Status |
|-----|-------|--------|
| I | Pendahuluan | Menurunkan masalah judul menjadi RM1--RM3 |
| II | Kajian Pustaka | Dasar netral untuk RM1--RM3 |
| III | Deskripsi Solusi | Keputusan rancangan konseptual |
| IV | Implementasi dan Evaluasi | Implementasi serta bukti dan batas evaluasi v2 |
| V | Kesimpulan dan Saran | Placeholder |

## Catatan rancangan penting

1. **Framing evaluasi**: BAB 1 dan BAB 4 menggunakan framing positive (technical validation yang dapat direplikasi). Studi yang melibatkan partisipan dan persetujuan etik diposisikan sebagai roadmap di BAB V.

2. **Hybrid retrieval**: Klaim hybrid di subbab II.5.7 secara eksplisit dispesifikkan sebagai hybrid by composition (lima sinyal terpisah yang dilampirkan ke konteks), bukan fusion ranking (RRF, MMR). Ekstensi ke unified fusion ranking dijabarkan sebagai roadmap.

3. **Latensi**: Strategi C dengan reframe trade-off deliberate. Sistem menyediakan dua mode operasi (normal vs streaming) dan dua tier model (cepat-singkat vs lebih bermakna). Diakui di subbab II.4.2.

4. **Persona AXIS**: Justifikasi di subbab II.2.3. Disiplin stabilitas lintas sesi diakui sebagai kontrak rancangan.

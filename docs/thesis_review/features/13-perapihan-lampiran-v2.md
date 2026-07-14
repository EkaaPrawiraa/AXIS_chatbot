# Perapihan Lampiran V2

**Tanggal:** 2026-07-14  
**Ruang lingkup:** naskah LaTeX V2 untuk seminar hasil dan laporan lengkap.

## Perubahan

- Semua tabel dan gambar lampiran menggunakan `\caption` bernomor sehingga masuk ke Daftar Tabel atau Daftar Gambar.
- Caption pada halaman lanjutan `longtable` tetap dicetak, tetapi tidak lagi menambah entri duplikat pada Daftar Tabel.
- Tujuh gambar antarmuka dan visualisasi graf pada Lampiran C diberi `\label` serta dirujuk dari narasi lampiran.
- Jalur sumber disederhanakan: `bab4.tex` dan `lampiran.tex` adalah sumber aktif; pembungkus lama `bab4_v2.tex`, `lampiran_v2.tex`, serta naskah seminar lama dihapus.
- README LaTeX diperbarui agar struktur sumber, margin, sitasi, dan perilaku caption lampiran sesuai konfigurasi yang dipakai.

## Verifikasi

`seminar_hasil_v2.tex` dan `main.tex` berhasil dikompilasi dengan `latexmk -pdf -bibtex`. Daftar Tabel kini memuat tabel lampiran bernomor A.1, B.1, dan seterusnya tanpa entri “Lanjutan” yang berulang. Tidak ada referensi atau sitasi yang tidak terselesaikan.

import { C, box, numberedCard, text, title } from "./common.mjs";
export async function slide12(presentation) {
  const slide = presentation.slides.add();
  title(slide, "EVALUASI", "Tiga jalur bukti dengan status yang dibedakan", 12);
  numberedCard(slide, "1", "Validasi fungsional", "Mengukur apakah komponen kritis dan percabangannya berjalan melalui test suite, benchmark, dan probe retrieval.", 70, 210, 340, 210, C.navy);
  numberedCard(slide, "2", "Kualitas percakapan & memori", "Membaca perilaku AXIS dan baseline melalui studi kasus, EPITOME, scripted persona, serta ablasi graf.", 470, 210, 340, 210, C.blue);
  numberedCard(slide, "3", "Pengalaman pengguna", "Pengujian mahasiswa dan pengukuran latensi suara telah dirancang, tetapi belum menjadi bukti seminar hasil.", 870, 210, 340, 210, C.amber);
  box(slide, 70, 500, 1140, 87, { fill: C.white, line: C.line, radius: true });
  text(slide, "Cara membaca hasil", 96, 523, 185, 22, { size: 15, color: C.blue, bold: true });
  text(slide, "Jalur 1 menghasilkan status lulus/gagal. Jalur 2 memberi indikasi yang harus dibaca bersama keterbatasannya. Jalur 3 adalah rencana evaluasi akhir.", 294, 519, 860, 38, { size: 18, color: C.ink, bold: true });
  return slide;
}

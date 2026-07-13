import { C, miniMetric, text, title } from "./common.mjs";
export async function slide13(presentation) {
  const slide = presentation.slides.add();
  title(slide, "EVALUASI", "Validasi fungsional: komponen kritis dan jejak keputusan bekerja", 13);
  miniMetric(slide, "59 / 59", "pengujian guardrail lulus", 70, 190, 230, C.navy);
  miniMetric(slide, "48 / 48", "pengujian kebijakan CBT lulus", 320, 190, 230, C.blue);
  miniMetric(slide, "24 / 24", "pengujian PHQ-9 lulus", 570, 190, 230, C.green);
  miniMetric(slide, "18 / 18", "node graf keputusan tercakup", 820, 190, 230, C.amber);
  miniMetric(slide, "15 / 15", "kueri Recall@5 menemukan fakta target", 210, 344, 270, C.navy);
  miniMetric(slide, "14 / 19", "eufemisme krisis tertangkap pada benchmark internal", 510, 344, 270, C.red);
  miniMetric(slide, "18 / 19", "cabang tercakup; satu cabang tidak terjangkau oleh desain", 810, 344, 270, C.blue);
  text(slide, "Interpretasi", 70, 530, 155, 22, { size: 15, color: C.blue, bold: true });
  text(slide, "Orkestrasi komponen kritis dapat dijalankan pada skenario yang diuji. Benchmark eufemisme tetap menunjukkan lima kasus yang belum tertangkap, sehingga belum cukup untuk menyatakan perlindungan krisis telah sempurna.", 70, 560, 1120, 50, { size: 18, color: C.ink, bold: true });
  return slide;
}

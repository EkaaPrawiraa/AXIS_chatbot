import { C, box, pill, simpleArrow, text, title } from "./common.mjs";
export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Memori jangka panjang: disaring, dihubungkan, lalu dipilih kembali", 9);
  box(slide, 70, 160, 565, 450, { fill: C.white, line: C.line, radius: true });
  await ctx.addImage(slide, {
    path: ctx.assetDir + "/report-figures/memory_concept_flow.png",
    left: 88, top: 180, width: 530, height: 390,
    fit: "contain",
    alt: "Flowchart konseptual penulisan dan siklus hidup memori dari laporan",
  });
  text(slide, "Gambar III.5 — penulisan dan siklus hidup memori", 90, 574, 525, 18, { size: 11, color: C.muted, align: "center" });
  text(slide, "Keputusan inti", 705, 184, 300, 25, { size: 20, color: C.navy, bold: true });
  const points = [
    "Sesi reguler disaring sebelum menjadi memori; administrasi PHQ-9 dan Confession Space dikecualikan.",
    "Graf menjaga hubungan antarmemori, sedangkan vektor membantu menemukan kemiripan semantik.",
    "Pemaknaan ulang dapat menggantikan memori lama; peluruhan dan pengarsipan membatasi konteks.",
  ];
  points.forEach((point, i) => {
    const y = 238 + i * 93;
    pill(slide, String(i + 1), 705, y, 38, { fill: i === 1 ? C.sky : C.greenSoft, color: i === 1 ? C.navy : C.green });
    text(slide, point, 760, y - 2, 400, 65, { size: 16, color: C.ink, bold: true });
  });
  box(slide, 705, 545, 445, 58, { fill: C.sky, line: C.sky, radius: true });
  text(slide, "Nilai graf yang diuji: kesinambungan konteks, relasi, dan lifecycle — bukan klaim otomatis peningkatan empati.", 725, 559, 405, 28, { size: 14, color: C.navy, bold: true, align: "center" });
  return slide;
}

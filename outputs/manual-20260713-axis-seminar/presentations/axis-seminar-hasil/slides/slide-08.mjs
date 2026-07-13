import { C, box, simpleArrow, text, title } from "./common.mjs";
export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Mood harian dan PHQ-9 masuk sebagai percakapan bertahap", 8);
  box(slide, 70, 160, 510, 445, { fill: C.white, line: C.line, radius: true });
  await ctx.addImage(slide, {
    path: ctx.assetDir + "/report-figures/phq9_concept_flow.png",
    left: 85, top: 178, width: 480, height: 387,
    fit: "contain",
    alt: "Flowchart konseptual mood dan PHQ-9 dari laporan",
  });
  text(slide, "Gambar III.4 — alur mood dan PHQ-9", 88, 570, 475, 18, { size: 11, color: C.muted, align: "center" });
  text(slide, "Empat keputusan pengalaman", 650, 184, 430, 25, { size: 19, color: C.navy, bold: true });
  const notes = [
    ["1", "Mood harian memberi konteks singkat, bukan diagnosis."],
    ["2", "Tawaran skrining mempertimbangkan waktu, percakapan, dan pilihan pengguna."],
    ["3", "Setiap item dapat dijawab melalui pilihan atau bahasa pengguna sendiri."],
    ["4", "Item keselamatan ditangani segera tanpa menunggu seluruh pengisian."],
  ];
  notes.forEach(([n, label], i) => {
    const y = 232 + i * 78;
    box(slide, 650, y, 44, 44, { fill: i === 3 ? C.amber : C.sky, line: i === 3 ? C.amber : C.sky, radius: true });
    text(slide, n, 650, y + 12, 44, 18, { size: 15, color: i === 3 ? C.white : C.navy, bold: true, align: "center" });
    text(slide, label, 720, y + 6, 440, 42, { size: 17, color: C.ink, bold: true });
  });
  box(slide, 650, 555, 495, 56, { fill: C.amberSoft, line: C.amberSoft, radius: true });
  text(slide, "PHQ-9 diposisikan sebagai skrining dan alat refleksi, bukan diagnosis.", 670, 572, 455, 22, { size: 15, color: C.ink, bold: true, align: "center" });
  return slide;
}

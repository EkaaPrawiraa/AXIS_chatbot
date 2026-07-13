import { C, box, text, title } from "./common.mjs";
export async function slide14(presentation, ctx) {
  const slide = presentation.slides.add();
  title(slide, "EVALUASI", "Bukti komparatif: hasilnya campuran dan tidak disederhanakan", 14);
  box(slide, 70, 176, 585, 362, { fill: C.white, line: C.line, radius: true });
  await ctx.addImage(slide, {
    path: ctx.assetDir + "/report-figures/epitome_chart_crop.png",
    left: 87, top: 195, width: 550, height: 320,
    fit: "contain",
    alt: "Grafik EPITOME dari laporan seminar hasil",
  });
  text(slide, "Gambar IV.14 — hasil EPITOME dari laporan", 90, 517, 545, 18, { size: 11, color: C.muted, align: "center" });
  box(slide, 710, 176, 500, 362, { fill: C.white, line: C.line, radius: true });
  text(slide, "Pembacaan hasil", 736, 206, 410, 28, { size: 21, color: C.navy, bold: true });
  text(slide, "Arya / cold-start", 736, 258, 200, 22, { size: 16, color: C.muted, bold: true });
  text(slide, "Baseline lebih tinggi pada ER, IP, dan EX.", 736, 290, 430, 25, { size: 18, color: C.ink, bold: true });
  text(slide, "Budi / memori kaya", 736, 350, 200, 22, { size: 16, color: C.muted, bold: true });
  text(slide, "AXIS sedikit lebih tinggi pada ER, setara pada IP, dan masih lebih rendah pada EX.", 736, 382, 440, 48, { size: 18, color: C.ink, bold: true });
  text(slide, "Ablasi: graf belum terbukti menaikkan skor empati EPITOME. Kontribusi yang lebih teramati adalah kesinambungan konteks dan lifecycle.", 736, 450, 430, 54, { size: 15, color: C.green, bold: true });
  text(slide, "Kesimpulan komparatif dibaca sebagai bukti awal pengembangan, bukan klaim superioritas umum.", 70, 575, 1120, 30, { size: 20, color: C.ink, bold: true, align: "center" });
  return slide;
}

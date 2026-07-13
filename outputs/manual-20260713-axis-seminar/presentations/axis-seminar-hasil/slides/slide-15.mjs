import { C, box, text, title } from "./common.mjs";
export async function slide15(presentation) {
  const slide = presentation.slides.add();
  title(slide, "PENUTUP", "Apa yang telah dijawab, dan apa yang masih harus dibuktikan", 15);
  const rows = [
    ["RM1", "Percakapan pendamping", "Parsial: teknik, batas keselamatan, dan alur bahasa terimplementasi; kualitas empati belum unggul konsisten."],
    ["RM2", "Mood dan PHQ-9", "Fungsional: orkestrasi, pengisian, keselamatan, dan penyimpanan asesmen telah lolos pengujian komponen."],
    ["RM3", "Memori jangka panjang", "Fungsional dan indikatif: penulisan, retrieval, lifecycle, serta Recall@5 berjalan; dampak graf pada empati belum terbukti."],
  ];
  rows.forEach(([id, heading, body], i) => {
    const y = 175 + i * 118;
    box(slide, 70, y, 1140, 92, { fill: C.white, line: C.line, radius: true });
    text(slide, id, 96, y + 28, 72, 28, { size: 20, color: C.navy, bold: true });
    text(slide, heading, 192, y + 18, 270, 25, { size: 18, color: C.ink, bold: true });
    text(slide, body, 472, y + 18, 685, 55, { size: 16, color: C.muted });
  });
  box(slide, 70, 558, 1140, 65, { fill: C.sky, line: C.sky, radius: true });
  text(slide, "Lanjutan menuju sidang akhir", 94, 579, 240, 21, { size: 15, color: C.navy, bold: true });
  text(slide, "Pengujian pengguna nyata, metrik latensi voice, serta penguatan benchmark bahasa informal dan eufemisme krisis.", 340, 575, 820, 28, { size: 17, color: C.ink, bold: true });
  text(slide, "Terima kasih", 70, 643, 1120, 25, { size: 21, color: C.navy, bold: true, align: "center" });
  return slide;
}

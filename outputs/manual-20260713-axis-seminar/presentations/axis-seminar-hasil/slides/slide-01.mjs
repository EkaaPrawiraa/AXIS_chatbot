import { C, W, H, box, line, text } from "./common.mjs";
export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = C.paper;
  box(slide, 0, 0, 42, H, { fill: C.navy, line: C.navy, lineWidth: 0 });
  box(slide, 42, 0, 10, H, { fill: C.blue, line: C.blue, lineWidth: 0 });
  text(slide, "SEMINAR HASIL TUGAS AKHIR", 90, 72, 450, 24, { size: 14, color: C.blue, bold: true });
  text(slide, "AXIS", 90, 122, 410, 72, { size: 58, color: C.navy, bold: true });
  text(slide, "Pengembangan arsitektur perangkat lunak companionship chatbot dengan memori jangka panjang berbasis knowledge graph untuk mahasiswa Indonesia", 92, 210, 725, 125, { size: 27, color: C.ink, bold: true });
  line(slide, 92, 360, 750, 360, { color: C.blue, width: 3 });
  text(slide, "Mohammad Nugraha Eka Prawira  |  13522001", 92, 390, 600, 27, { size: 18, color: C.ink, bold: true });
  text(slide, "Program Studi Informatika, STEI ITB\nPembimbing: Dr. Agung Dewandaru, S.T., M.Sc.\n2026", 92, 430, 600, 78, { size: 16, color: C.muted });
  box(slide, 872, 82, 250, 440, { fill: C.white, line: C.line, radius: true });
  await ctx.addImage(slide, {
    path: ctx.assetDir + "/report-figures/chat_main.png",
    left: 884, top: 95, width: 226, height: 404,
    fit: "contain",
    alt: "Tangkapan antarmuka percakapan AXIS",
  });
  text(slide, "Tangkapan antarmuka AXIS", 875, 530, 244, 20, { size: 11, color: C.muted, align: "center" });
  box(slide, 842, 570, 310, 65, { fill: C.sky, line: C.sky, radius: true });
  text(slide, "Rancangan, implementasi, dan bukti awal evaluasi", 856, 590, 280, 28, { size: 15, color: C.navy, bold: true, align: "center" });
  text(slide, "INFORMATIKA  •  STEI ITB", 90, 666, 500, 18, { size: 11, color: C.muted, bold: true });
  return slide;
}

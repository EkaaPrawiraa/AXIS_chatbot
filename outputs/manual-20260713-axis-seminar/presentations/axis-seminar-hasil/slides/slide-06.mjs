import { C, box, simpleArrow, text, title } from "./common.mjs";
export async function slide06(presentation) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Alur solusi AXIS dari percakapan hingga memori", 6);
  const steps = [
    ["1", "Pengguna", "menulis, berbicara, atau mencatat mood"],
    ["2", "Memahami kondisi", "bahasa, konteks, dan batas keselamatan"],
    ["3", "Merespons", "refleksi CBT, informasi, atau rujukan"],
    ["4", "Menutup sesi", "sesi aktif selesai tanpa mengganggu percakapan"],
    ["5", "Menulis memori", "sesi reguler disaring dan diringkas secara asinkron"],
  ];
  steps.forEach(([n, h, b], i) => {
    const x = 60 + i * 244;
    box(slide, x, 250, 200, 182, { fill: C.white, line: C.line, radius: true });
    text(slide, n, x + 18, 270, 35, 25, { size: 15, color: C.blue, bold: true });
    text(slide, h, x + 18, 307, 164, 30, { size: 19, color: C.ink, bold: true });
    text(slide, b, x + 18, 352, 164, 52, { size: 14, color: C.muted });
    if (i < 4) simpleArrow(slide, x + 204, 318);
  });
  box(slide, 70, 512, 1140, 86, { fill: C.greenSoft, line: C.greenSoft, radius: true });
  text(slide, "Batas penting", 95, 533, 138, 22, { size: 15, color: C.green, bold: true });
  text(slide, "Confession Space adalah percakapan suara sementara. Transkripnya membantu interaksi saat itu, tetapi tidak masuk ke penulisan memori jangka panjang AXIS.", 250, 530, 920, 35, { size: 17, color: C.ink });
  return slide;
}

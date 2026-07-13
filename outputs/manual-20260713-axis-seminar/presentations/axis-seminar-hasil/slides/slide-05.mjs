import { C, box, text, title } from "./common.mjs";
export async function slide05(presentation) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Lima kebutuhan mengikat tiga rumusan masalah", 5);
  text(slide, "K1–K3 menjawab rumusan masalah utama. K4 dan K5 adalah kebutuhan lintas-rumusan agar pengalaman pendampingan tetap aman dan dapat dikendalikan.", 70, 158, 1120, 38, { size: 18, color: C.muted });
  const cards = [
    ["K1", "Percakapan bermakna", C.navy],
    ["K2", "Mood dan PHQ-9", C.blue],
    ["K3", "Memori jangka panjang", C.green],
    ["K4", "Batas keselamatan", C.amber],
    ["K5", "Kendali pengguna", C.red],
  ];
  cards.forEach(([id, label, color], i) => {
    const x = 70 + i * 228;
    box(slide, x, 260, 190, 185, { fill: C.white, line: C.line, radius: true });
    box(slide, x + 22, 282, 45, 45, { fill: color, line: color, radius: true });
    text(slide, id, x + 22, 294, 45, 18, { size: 17, color: C.white, bold: true, align: "center" });
    text(slide, label, x + 18, 350, 154, 48, { size: 18, color: C.ink, bold: true, align: "center" });
  });
  text(slide, "Prinsip desain", 70, 515, 190, 22, { size: 15, color: C.blue, bold: true });
  text(slide, "Setiap fitur harus membantu percakapan tetap relevan, aman, atau dapat dikendalikan pengguna. Fitur tidak diperlakukan sebagai daftar teknologi yang berdiri sendiri.", 70, 546, 1110, 54, { size: 21, color: C.ink, bold: true });
  return slide;
}

import { C, box, pill, simpleArrow, text, title } from "./common.mjs";
export async function slide07(presentation) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Percakapan reflektif: respons mengikuti kondisi pengguna", 7);
  const stages = [
    ["Pesan pengguna", "bahasa informal dan campuran dikenali"],
    ["Sinyal percakapan", "emosi, kebutuhan, dan risiko dibaca"],
    ["Kebijakan dialog", "teknik reflektif dipilih bila relevan"],
    ["Respons aman", "batas non-klinis dan rujukan berlaku saat perlu"],
  ];
  stages.forEach(([h,b], i) => {
    const x = 70 + i * 285;
    box(slide, x, 210, 232, 148, { fill: C.white, line: C.line, radius: true });
    text(slide, h, x + 18, 235, 196, 27, { size: 18, bold: true, align: "center" });
    text(slide, b, x + 18, 282, 196, 42, { size: 14, color: C.muted, align: "center" });
    if (i < 3) simpleArrow(slide, x + 232, 266);
  });
  text(slide, "Teknik yang dapat muncul", 70, 425, 230, 22, { size: 15, color: C.blue, bold: true });
  const labels = ["Validasi", "Reframing", "Thought record", "Grounding", "Aktivasi perilaku", "Psikoedukasi", "Self-compassion"];
  labels.forEach((label, i) => pill(slide, label, 70 + (i % 4) * 280, 462 + Math.floor(i / 4) * 48, 245, { fill: i === 3 ? C.greenSoft : C.sky, color: i === 3 ? C.green : C.navy }));
  text(slide, "Teknik bukan menu yang dipaksakan. Sistem dapat memilih validasi atau percakapan biasa ketika teknik baru tidak diperlukan.", 70, 586, 1110, 35, { size: 18, color: C.ink, bold: true });
  return slide;
}

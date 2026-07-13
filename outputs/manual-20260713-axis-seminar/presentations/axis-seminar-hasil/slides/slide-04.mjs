import { C, box, pill, text, title } from "./common.mjs";
export async function slide04(presentation) {
  const slide = presentation.slides.add();
  title(slide, "SOLUSI", "Posisi AXIS: pendamping non-klinis yang terintegrasi", 4);
  box(slide, 70, 170, 1140, 305, { fill: C.white, line: C.line, radius: true });
  text(slide, "AXIS", 108, 205, 180, 45, { size: 34, color: C.navy, bold: true });
  text(slide, "dirancang untuk menemani proses refleksi sehari-hari, bukan mendiagnosis atau menggantikan bantuan profesional.", 108, 260, 760, 44, { size: 20, color: C.ink, bold: true });
  pill(slide, "Percakapan reflektif", 108, 340, 194, { fill: C.sky });
  pill(slide, "Mood & PHQ-9", 322, 340, 150, { fill: C.sky });
  pill(slide, "Memori berkelanjutan", 492, 340, 185, { fill: C.sky });
  pill(slide, "Kendali pengguna", 697, 340, 164, { fill: C.sky });
  pill(slide, "Batas keselamatan", 881, 340, 170, { fill: C.sky });
  text(slide, "Fitur pendukung companionship", 70, 526, 310, 22, { size: 15, color: C.blue, bold: true });
  text(slide, "Ruang percakapan suara sementara, bantuan dan hotline, visibilitas memori sensitif, penghapusan data, serta ekspor data ditempatkan sebagai cara pengguna mengatur pengalaman pendampingannya.", 70, 558, 1125, 54, { size: 18, color: C.muted });
  return slide;
}

import { C, numberedCard, title, text } from "./common.mjs";
export async function slide03(presentation) {
  const slide = presentation.slides.add();
  title(slide, "MASALAH", "Tiga pertanyaan yang menjadi jangkar pengembangan", 3);
  numberedCard(slide, "RM1", "Percakapan pendamping", "Bagaimana membangun percakapan yang empatik, bermakna, dan aman dalam bahasa informal maupun campuran mahasiswa Indonesia?", 70, 164, 1135, 114, C.navy);
  numberedCard(slide, "RM2", "Mood dan PHQ-9", "Bagaimana pemantauan kondisi emosional masuk ke alur percakapan secara bertahap tanpa terasa sebagai proses klinis yang terpisah?", 70, 302, 1135, 114, C.blue);
  numberedCard(slide, "RM3", "Memori jangka panjang", "Bagaimana memori dapat ditulis, dihubungkan, diperbarui, dan dipilih kembali agar percakapan lintas sesi tetap berkesinambungan?", 70, 440, 1135, 114, C.green);
  text(slide, "Ukuran keberhasilan", 70, 605, 210, 22, { size: 14, color: C.blue, bold: true });
  text(slide, "Dibuktikan melalui fungsi komponen, ketahanan skenario kritis, kemampuan pemanggilan kembali memori, serta pembandingan perilaku percakapan.", 70, 634, 1070, 28, { size: 17, color: C.muted });
  return slide;
}

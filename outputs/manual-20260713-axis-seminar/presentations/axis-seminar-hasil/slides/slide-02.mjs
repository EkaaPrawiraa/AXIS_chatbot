import { C, numberedCard, title, text } from "./common.mjs";
export async function slide02(presentation) {
  const slide = presentation.slides.add();
  title(slide, "MASALAH", "Dukungan yang berkelanjutan, bukan sekadar jawaban satu kali", 2);
  text(slide, "Mahasiswa membutuhkan ruang percakapan non-klinis yang dapat mengikuti konteks hidupnya tanpa mengambil alih peran tenaga profesional.", 70, 155, 1040, 48, { size: 21, color: C.muted });
  numberedCard(slide, "1", "Percakapan mudah terputus", "Chatbot dapat memberi respons hangat, tetapi konteks akademik dan relasi penting sering harus diceritakan ulang.", 70, 248, 335, 190, C.navy);
  numberedCard(slide, "2", "Refleksi perlu terasa wajar", "Pemeriksaan emosi tidak boleh memutus percakapan atau membuat pengguna merasa sedang menjalani proses klinis.", 472, 248, 335, 190, C.blue);
  numberedCard(slide, "3", "Pengguna perlu tetap memegang kendali", "Memori, data, dan ruang percakapan sementara memerlukan batas yang dapat dipahami dan dikendalikan pengguna.", 874, 248, 335, 190, C.green);
  text(slide, "Kesenjangan yang diangkat", 70, 495, 310, 24, { size: 14, color: C.blue, bold: true });
  text(slide, "Sistem yang ada menunjukkan potongan kemampuan, tetapi belum menyatukan percakapan reflektif, skrining ringan, memori relasional, dan kendali pengguna untuk konteks mahasiswa Indonesia.", 70, 528, 1110, 70, { size: 24, color: C.ink, bold: true });
  return slide;
}

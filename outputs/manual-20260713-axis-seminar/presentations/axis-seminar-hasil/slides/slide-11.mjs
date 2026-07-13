import { C, box, text, title } from "./common.mjs";
export async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  title(slide, "IMPLEMENTASI", "Fitur pengguna menyajikan arsitektur sebagai pengalaman pendampingan", 11);
  const phones = [
    ["chat_main.png", "Chat dan refleksi", "Percakapan utama, teknik CBT, pilihan PHQ-9, dan respons keselamatan."],
    ["confession_space.png", "Suara sementara", "Confession Space untuk bicara dengan subtitle tanpa menjadi memori jangka panjang AXIS."],
    ["memory_dashboard.png", "Memori dan kendali", "Melihat memori, menyembunyikan konten sensitif, mengubah atau menghapus data."],
  ];
  for (let i = 0; i < phones.length; i += 1) {
    const [asset, heading, body] = phones[i];
    const x = 125 + i * 362;
    box(slide, x, 170, 270, 360, { fill: C.white, line: C.line, radius: true });
    await ctx.addImage(slide, {
      path: ctx.assetDir + "/report-figures/" + asset,
      left: x + 14, top: 184, width: 242, height: 322,
      fit: "contain",
      alt: heading,
    });
    text(slide, heading, x + 15, 548, 240, 27, { size: 18, color: C.navy, bold: true, align: "center" });
    text(slide, body, x + 12, 584, 246, 50, { size: 13, color: C.muted, align: "center" });
  }
  return slide;
}

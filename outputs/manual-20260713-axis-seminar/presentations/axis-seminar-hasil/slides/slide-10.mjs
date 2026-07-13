import { C, box, text, title } from "./common.mjs";
export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  title(slide, "IMPLEMENTASI", "Topologi pipeline agentik AXIS", 10);
  text(slide, "Alur pemrosesan pesan", 70, 180, 410, 28, { size: 22, color: C.navy, bold: true });

  box(slide, 70, 232, 490, 120, { fill: C.sky, line: C.line, radius: true });
  text(slide, "Jalur sinkron", 94, 255, 180, 22, { size: 18, color: C.navy, bold: true });
  text(slide, "Aplikasi web → gateway → orkestrasi percakapan → respons pengguna.", 94, 291, 430, 36, { size: 17, color: C.ink, bold: true });

  box(slide, 70, 383, 490, 120, { fill: C.greenSoft, line: C.line, radius: true });
  text(slide, "Jalur asinkron", 94, 406, 190, 22, { size: 18, color: C.green, bold: true });
  text(slide, "Sesi tidak aktif → finalisasi → ekstraksi dan penyimpanan memori hibrid.", 94, 442, 430, 36, { size: 17, color: C.ink, bold: true });

  text(slide, "Pemisahan ini menjaga pekerjaan ekstraksi memori tidak menambah waktu tunggu pada giliran chat.", 70, 542, 490, 50, { size: 17, color: C.muted });
  box(slide, 70, 615, 490, 54, { fill: C.white, line: C.line, radius: true });
  text(slide, "Routing utama: masukan audio, mode PHQ-9, eskalasi krisis, dan keluaran suara.", 92, 631, 445, 22, { size: 13, color: C.muted, bold: true });

  box(slide, 615, 150, 595, 510, { fill: C.white, line: C.line, radius: true });
  text(slide, "Topologi satu giliran percakapan", 650, 170, 470, 18, { size: 13, color: C.clay, bold: true });
  const panels = [
    { label: "Masukan & konteks", path: "langgraph-01.png", x: 642 },
    { label: "Pemilihan respons", path: "langgraph-02.png", x: 825 },
    { label: "Keselamatan & keluaran", path: "langgraph-03.png", x: 1008 },
  ];
  for (const panel of panels) {
    box(slide, panel.x, 202, 164, 387, { fill: C.paper, line: C.line, radius: true });
    text(slide, panel.label, panel.x + 10, 214, 144, 26, { size: 11, color: C.navy, bold: true, align: "center" });
    await ctx.addImage(slide, {
      path: ctx.assetDir + "/report-figures/langgraph-crops/" + panel.path,
      left: panel.x + 8, top: 244, width: 148, height: 330,
      fit: "contain",
      alt: panel.label + " dalam topologi pipeline agentik AXIS",
    });
  }
  text(slide, "Urutan asli dibaca dari kiri ke kanan: tiga panel adalah potongan berurutan dari satu diagram LangGraph.", 650, 597, 520, 19, { size: 11, color: C.muted, align: "center" });
  text(slide, "Gambar IV.2 — topologi implementasi pipeline agentik AXIS", 632, 625, 560, 18, { size: 11, color: C.muted, align: "center" });
  return slide;
}

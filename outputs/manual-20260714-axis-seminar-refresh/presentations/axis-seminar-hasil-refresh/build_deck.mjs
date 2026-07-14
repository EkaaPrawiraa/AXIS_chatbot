import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import {
  createSlideContext,
  ensureArtifactToolWorkspace,
  importArtifactTool,
  saveBlobToFile,
} from "/Users/ekaaprawira/.codex/plugins/cache/openai-primary-runtime/presentations/26.601.10930/skills/presentations/scripts/artifact_tool_utils.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../../../../");
const assetDir = path.join(__dirname, "assets");
const outPath = path.join(__dirname, "AXIS_Seminar_Hasil_2026_Lengkap.pptx");
const previewDir = path.join(__dirname, "preview");
const layoutDir = path.join(__dirname, "layout");

const W = 1280;
const H = 720;
const C = {
  paper: "#FFFAF4",
  white: "#FFFDF9",
  ink: "#2D2119",
  coffee: "#4F3424",
  clay: "#8B5438",
  line: "#E5D4C3",
  muted: "#8A7667",
  green: "#6C7B53",
  greenSoft: "#EDF0E5",
  amber: "#C8924F",
  amberSoft: "#F9ECD2",
  red: "#A85F5D",
  redSoft: "#F7DDD0",
};

function addBox(slide, left, top, width, height, { fill = C.white, line = C.line, radius = false, lineWidth = 1 } = {}) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left, top, width, height },
    fill,
    line: { width: lineWidth, fill: line },
  });
}

function addText(slide, value, left, top, width, height, options = {}) {
  const shape = slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill: options.fill || "none",
    line: { width: 0, fill: "none" },
  });
  shape.text.add(value);
  shape.text.fontSize = options.size || 18;
  shape.text.color = options.color || C.ink;
  shape.text.typeface = options.font || "Arial";
  shape.text.alignment = options.align || "left";
  shape.text.insets = { left: options.inset || 0, right: options.inset || 0, top: options.inset || 0, bottom: options.inset || 0 };
  if (options.bold) shape.text.bold = true;
  if (options.italic) shape.text.italic = true;
  return shape;
}

function addRule(slide, x1, y1, x2, y2, color = C.line, width = 1) {
  return slide.shapes.add({
    geometry: "line",
    position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 },
    line: { width, fill: color },
  });
}

function footer(slide, active, number) {
  const labels = ["MASALAH", "SOLUSI", "IMPLEMENTASI", "EVALUASI", "BANK ARTEFAK"];
  const activeLabel = active.toUpperCase();
  let x = 70;
  for (const label of labels) {
    const on = activeLabel === label;
    addText(slide, label, x, 684, 132, 16, { size: 9, color: on ? C.coffee : C.muted, bold: on, align: "center" });
    addRule(slide, x, 705, x + 132, 705, on ? C.coffee : C.line, on ? 3 : 1);
    x += 142;
  }
  addText(slide, String(number).padStart(3, "0"), 1148, 682, 62, 18, { size: 10, color: C.muted, align: "right" });
}

function slideTitle(slide, section, heading, number, note = "") {
  slide.background.fill = C.paper;
  addText(slide, section.toUpperCase(), 70, 38, 420, 20, { size: 11, color: C.clay, bold: true });
  addText(slide, heading, 70, 66, 1080, 44, { size: 30, color: C.ink, bold: true });
  addRule(slide, 70, 128, 1210, 128, C.line, 1);
  if (note) addText(slide, note, 70, 140, 1030, 18, { size: 11, color: C.muted });
  footer(slide, section, number);
}

function metric(slide, value, label, left, top, width, accent = C.coffee) {
  addBox(slide, left, top, width, 104, { fill: C.white, line: C.line, radius: true });
  addText(slide, value, left + 8, top + 18, width - 16, 32, { size: 27, color: accent, bold: true, align: "center" });
  addText(slide, label, left + 16, top + 61, width - 32, 28, { size: 12, color: C.muted, align: "center" });
}

function cleaned(text) {
  return text
    .replace(/\\ignorespaces/g, "")
    .replace(/\\textit\s*\{([^}]*)\}/g, "$1")
    .replace(/\\textbf\s*\{([^}]*)\}/g, "$1")
    .replace(/\\allowbreak/g, "")
    .replace(/\\_/g, "_")
    .replace(/\\#/g, "#")
    .replace(/\\[a-zA-Z]+/g, "")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function parseLot(filePath, kind) {
  const source = await fs.readFile(filePath, "utf8");
  return source.split("\n")
    .filter((line) => line.includes(`\\contentsline {${kind}}`))
    .map((line) => {
      const id = line.match(/\\numberline \{([^}]+)\}/)?.[1] || "?";
      const page = Number(line.match(/\}\{(\d+)\}\{(?:table|figure)\./)?.[1] || line.match(/\}\{(\d+)\}\%$/)?.[1] || 0);
      const titleMatch = line.match(/\\numberline \{[^}]+\}\{\\ignorespaces (.*)\}\{\d+\}/);
      return { id, page, title: cleaned(titleMatch?.[1] || `${kind} ${id}`) };
    })
    .filter((entry) => entry.page > 0);
}

async function hasFile(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function addImageOrPlaceholder(slide, ctx, filePath, left, top, width, height, label) {
  if (await hasFile(filePath)) {
    addBox(slide, left - 4, top - 4, width + 8, height + 8, { fill: C.white, line: C.line, radius: true });
    await ctx.addImage(slide, { path: filePath, left, top, width, height, fit: "contain", alt: label });
    return;
  }
  addBox(slide, left, top, width, height, { fill: C.redSoft, line: C.red, radius: true });
  addText(slide, "PLACEHOLDER\nAset belum tersedia", left + 30, top + height / 2 - 30, width - 60, 60, { size: 18, color: C.red, bold: true, align: "center" });
  addText(slide, label, left + 24, top + height - 38, width - 48, 20, { size: 10, color: C.muted, align: "center" });
}

async function addCoreSlides(presentation, artifact, slides) {
  const ctxFor = (number) => createSlideContext(artifact, { slideSize: { width: W, height: H }, slideNumber: number, outputDir: __dirname, assetDir, workspaceDir: __dirname });

  const add = async (section, heading, draw) => {
    const slide = presentation.slides.add();
    const number = presentation.slides.count;
    slideTitle(slide, section, heading, number);
    await draw(slide, ctxFor(number), number);
    slides.push(slide);
  };

  {
    const slide = presentation.slides.add();
    const number = presentation.slides.count;
    slide.background.fill = C.paper;
    addBox(slide, 0, 0, 42, H, { fill: C.coffee, line: C.coffee, lineWidth: 0 });
    addBox(slide, 42, 0, 10, H, { fill: C.clay, line: C.clay, lineWidth: 0 });
    addText(slide, "SEMINAR HASIL TUGAS AKHIR", 90, 72, 520, 22, { size: 13, color: C.clay, bold: true });
    addText(slide, "AXIS", 90, 118, 420, 62, { size: 56, color: C.coffee, bold: true });
    addText(slide, "Pengembangan Companionship Chatbot dengan Asesmen Depresi melalui Percakapan dan Memori Jangka Panjang Berbasis Knowledge Graph untuk Mahasiswa Indonesia", 92, 204, 680, 140, { size: 26, color: C.ink, bold: true });
    addRule(slide, 92, 365, 750, 365, C.clay, 3);
    addText(slide, "Mohammad Nugraha Eka Prawira  |  13522001", 92, 392, 600, 26, { size: 17, color: C.ink, bold: true });
    addText(slide, "Program Studi Informatika, STEI ITB\nPembimbing: Dr. Agung Dewandaru, S.T., M.Sc.\n2026", 92, 430, 600, 74, { size: 15, color: C.muted });
    addBox(slide, 842, 72, 286, 494, { fill: C.white, line: C.line, radius: true });
    await addImageOrPlaceholder(slide, ctxFor(number), path.join(assetDir, "app", "03_chat_main.png"), 865, 94, 240, 430, "Tampilan percakapan AXIS");
    addText(slide, "Purwarupa AXIS pada antarmuka web", 855, 536, 260, 18, { size: 11, color: C.muted, align: "center" });
    addBox(slide, 842, 585, 286, 54, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "Rancangan, implementasi, evaluasi", 858, 602, 254, 20, { size: 14, color: C.coffee, bold: true, align: "center" });
    addText(slide, "INFORMATIKA • STEI ITB", 90, 667, 500, 16, { size: 10, color: C.muted, bold: true });
    slides.push(slide);
  }

  await add("MASALAH", "Mahasiswa membutuhkan pendampingan yang mengingat konteks, tetapi tetap berada di batas non-klinis", async (slide) => {
    const cards = [
      ["Percakapan putus", "Respons satu kali sulit mengikuti tekanan akademik, relasi, dan perubahan hidup yang berulang."],
      ["Skrining terasa terpisah", "Pemeriksaan suasana hati dan PHQ-9 perlu hadir sukarela, bukan menjadi formulir yang memutus percakapan."],
      ["Memori perlu berubah", "Konteks lama harus dapat diperbarui ketika pengguna menafsirkan ulang pengalaman atau menemukan cara menghadapi masalah."],
    ];
    addText(slide, "Kesenjangan yang dituju", 70, 176, 320, 24, { size: 20, color: C.coffee, bold: true });
    cards.forEach(([heading, body], index) => {
      const x = 70 + index * 376;
      addBox(slide, x, 224, 346, 212, { fill: C.white, line: C.line, radius: true });
      addBox(slide, x + 20, 244, 32, 32, { fill: [C.coffee, C.clay, C.green][index], line: [C.coffee, C.clay, C.green][index], radius: true });
      addText(slide, String(index + 1), x + 20, 250, 32, 18, { size: 15, color: C.white, bold: true, align: "center" });
      addText(slide, heading, x + 68, 244, 250, 26, { size: 18, color: C.ink, bold: true });
      addText(slide, body, x + 24, 296, 298, 96, { size: 15, color: C.muted });
    });
    addBox(slide, 70, 486, 1120, 94, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "AXIS menyatukan percakapan reflektif, asesmen skrining depresi secara percakapan, dan memori jangka panjang berelasi dalam satu pengalaman yang dapat dikendalikan pengguna.", 98, 514, 1060, 42, { size: 19, color: C.coffee, bold: true, align: "center" });
  });

  await add("MASALAH", "Tiga rumusan masalah membentuk benang merah laporan", async (slide) => {
    const rows = [
      ["RM1", "Percakapan pendamping", "Bagaimana membangun respons empatik, reflektif, aman, dan sesuai cara mahasiswa Indonesia mengekspresikan diri?", C.coffee],
      ["RM2", "Asesmen depresi percakapan", "Bagaimana mood harian dan PHQ-9 diorkestrasi secara sukarela, bertahap, dan non-diagnostik?", C.clay],
      ["RM3", "Memori jangka panjang", "Bagaimana konteks lintas sesi ditulis, dihubungkan, diperbarui, dan dipilih kembali ketika kehidupan mahasiswa berubah?", C.green],
    ];
    rows.forEach(([code, heading, body, accent], index) => {
      const y = 188 + index * 132;
      addBox(slide, 90, y, 1100, 100, { fill: C.white, line: C.line, radius: true });
      addBox(slide, 112, y + 25, 56, 50, { fill: accent, line: accent, radius: true });
      addText(slide, code, 112, y + 41, 56, 20, { size: 15, color: C.white, bold: true, align: "center" });
      addText(slide, heading, 194, y + 20, 360, 24, { size: 18, color: C.ink, bold: true });
      addText(slide, body, 194, y + 50, 920, 32, { size: 14, color: C.muted });
    });
  });

  await add("SOLUSI", "AXIS menghubungkan fitur menjadi satu pengalaman companionship", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "solution_use_case.png"), 70, 168, 515, 402, "Diagram use case AXIS");
    const blocks = [
      ["Percakapan reflektif", "Chat, CBT non-klinis, pengayaan bahasa, dan batas keselamatan."],
      ["Asesmen bertahap", "Mood harian dan PHQ-9 sebagai skrining, bukan diagnosis."],
      ["Kontinuitas", "Memori relasional, lifecycle, transparansi, dan kendali pengguna."],
    ];
    blocks.forEach(([heading, body], index) => {
      const y = 186 + index * 126;
      addBox(slide, 640, y, 520, 96, { fill: C.white, line: C.line, radius: true });
      addText(slide, heading, 668, y + 18, 450, 23, { size: 18, color: C.coffee, bold: true });
      addText(slide, body, 668, y + 50, 450, 25, { size: 14, color: C.muted });
    });
    addText(slide, "Gambar III.1 — Diagram use case AXIS", 88, 585, 475, 18, { size: 11, color: C.muted, align: "center" });
  });

  await add("SOLUSI", "Alur solusi memisahkan respons saat ini dari proses membangun ingatan", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "solution_overview_flow.png"), 95, 182, 1090, 340, "Flowchart penggunaan AXIS");
    addBox(slide, 95, 552, 1090, 68, { fill: C.greenSoft, line: C.greenSoft, radius: true });
    addText(slide, "Respons percakapan berlangsung pada jalur aktif; penyaringan dan penulisan memori terjadi setelah sesi tidak aktif agar tidak mengganggu pengalaman chat.", 120, 574, 1040, 24, { size: 16, color: C.coffee, bold: true, align: "center" });
  });

  await add("SOLUSI", "Kebijakan dialog memilih bantuan reflektif tanpa memaksakan teknik", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "cbt_dialogue_flow.png"), 72, 168, 610, 430, "Alur pemilihan teknik CBT");
    const techniques = ["Validasi", "Reframing", "Thought record", "Grounding", "Aktivasi perilaku", "Psikoedukasi", "Self-compassion"];
    addText(slide, "Teknik yang dapat muncul", 740, 180, 350, 24, { size: 18, color: C.coffee, bold: true });
    techniques.forEach((label, index) => {
      const x = 740 + (index % 2) * 190;
      const y = 226 + Math.floor(index / 2) * 60;
      addBox(slide, x, y, 168, 38, { fill: index === 3 ? C.amberSoft : C.white, line: C.line, radius: true });
      addText(slide, label, x + 8, y + 10, 152, 18, { size: 12, color: C.ink, bold: true, align: "center" });
    });
    addBox(slide, 736, 484, 390, 90, { fill: C.redSoft, line: C.redSoft, radius: true });
    addText(slide, "PHQ-9 aktif atau risiko krisis menghentikan pemilihan teknik agar percakapan mengikuti jalur keselamatan yang tepat.", 760, 507, 342, 42, { size: 14, color: C.coffee, bold: true, align: "center" });
  });

  await add("SOLUSI", "Mood harian memberi konteks; PHQ-9 menjadi skrining depresi yang bersifat sukarela", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "phq9_concept_flow.png"), 70, 168, 570, 435, "Flowchart konseptual mood dan PHQ-9");
    const points = [
      "Mood hanya membantu membaca konteks hari ini dan tren singkat.",
      "PHQ-9 ditawarkan oleh kondisi adaptif, bukan dipaksakan sebagai formulir.",
      "Jawaban bebas dapat diklarifikasi; hasil tetap skrining, bukan diagnosis.",
      "Item kesembilan dapat mengaktifkan rute keselamatan sebelum asesmen selesai.",
    ];
    points.forEach((body, index) => {
      const y = 186 + index * 96;
      addBox(slide, 700, y, 435, 72, { fill: index === 3 ? C.redSoft : C.white, line: C.line, radius: true });
      addText(slide, String(index + 1), 720, y + 24, 28, 20, { size: 14, color: index === 3 ? C.red : C.clay, bold: true, align: "center" });
      addText(slide, body, 762, y + 17, 340, 42, { size: 14, color: C.ink, bold: true });
    });
  });

  await add("SOLUSI", "Memori jangka panjang disaring, dihubungkan, lalu dapat ditafsirkan ulang", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "memory_concept_flow.png"), 68, 168, 590, 430, "Flowchart penulisan dan lifecycle memori");
    const notes = [
      ["Saring", "Administrasi PHQ-9 dan sesi suara sementara tidak menjadi memori."],
      ["Hubungkan", "Pengalaman, emosi, pikiran, perilaku, pemicu, topik, dan subjek membentuk konteks relasional."],
      ["Perbarui", "Supersession, reappraisal, penonaktifan, dan peluruhan menjaga memori lama tidak mendominasi."],
    ];
    notes.forEach(([heading, body], index) => {
      const y = 178 + index * 130;
      addBox(slide, 720, y, 410, 102, { fill: C.white, line: C.line, radius: true });
      addText(slide, heading, 747, y + 18, 330, 24, { size: 17, color: C.green, bold: true });
      addText(slide, body, 747, y + 52, 350, 38, { size: 13, color: C.muted });
    });
  });

  await add("IMPLEMENTASI", "Arsitektur memisahkan pengalaman pengguna, layanan inti, dan penyimpanan memori", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "system_architecture.png"), 535, 158, 648, 450, "Arsitektur implementasi AXIS");
    const rows = [
      ["Jalur sinkron", "Web → backend → orkestrasi → respons pengguna."],
      ["Jalur asinkron", "Sesi tidak aktif → finalisasi → ekstraksi dan sinkronisasi memori."],
      ["Penyimpanan", "PostgreSQL/pgvector untuk data relasional dan semantik; Neo4j untuk struktur relasional; Redis untuk state sementara."],
    ];
    rows.forEach(([heading, body], index) => {
      const y = 192 + index * 130;
      addBox(slide, 70, y, 404, 100, { fill: index === 1 ? C.greenSoft : C.white, line: C.line, radius: true });
      addText(slide, heading, 96, y + 18, 300, 22, { size: 17, color: C.coffee, bold: true });
      addText(slide, body, 96, y + 50, 348, 34, { size: 13, color: C.muted });
    });
  });

  await add("IMPLEMENTASI", "Antarmuka menghadirkan percakapan, ruang suara sementara, dan memori yang dapat dilihat pengguna", async (slide, ctx) => {
    const items = [
      ["03_chat_main.png", "Percakapan utama", "Chat, chip PHQ-9, dan respons streaming."],
      ["04_confession_space.png", "Confession Space", "Percakapan suara sementara dengan subtitle; tidak masuk finalisasi memori."],
      ["05_memories_dashboard.png", "Memori dan kendali", "Cari, lihat kategori, koreksi, dan sembunyikan konten sensitif."],
    ];
    for (let index = 0; index < items.length; index += 1) {
      const [file, heading, body] = items[index];
      const x = 68 + index * 400;
      addBox(slide, x, 184, 360, 404, { fill: C.white, line: C.line, radius: true });
      await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "app", file), x + 70, 204, 220, 246, heading);
      addText(slide, heading, x + 24, 472, 312, 22, { size: 16, color: C.coffee, bold: true, align: "center" });
      addText(slide, body, x + 30, 508, 300, 45, { size: 12, color: C.muted, align: "center" });
    }
  });

  await add("EVALUASI", "Evaluasi menggabungkan kontrak sistem, penilaian buta, dan benchmark terarah", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "evaluation_three_tracks.png"), 80, 176, 490, 382, "Tiga jalur evaluasi AXIS");
    const rows = [
      ["Fungsional", "Apakah kontrak komponen kritis berjalan pada skenario yang didefinisikan?"],
      ["Kualitas", "Apakah respons, orkestrasi PHQ-9, dan penggunaan memori memenuhi rubrik atau label acuan?"],
      ["Pengguna nyata", "Direncanakan sebagai evaluasi lanjutan; belum dipakai untuk klaim hasil pada presentasi ini."],
    ];
    rows.forEach(([heading, body], index) => {
      const y = 184 + index * 116;
      addBox(slide, 650, y, 472, 86, { fill: index === 2 ? C.amberSoft : C.white, line: C.line, radius: true });
      addText(slide, heading, 678, y + 16, 150, 20, { size: 16, color: C.coffee, bold: true });
      addText(slide, body, 678, y + 43, 410, 30, { size: 12, color: C.muted });
    });
  });

  await add("EVALUASI", "Validasi kontrak menunjukkan semua kelompok komponen yang diuji lulus", async (slide) => {
    metric(slide, "54/54", "kebijakan dialog CBT", 70, 190, 198, C.coffee);
    metric(slide, "80/80", "kontrak guardrail", 290, 190, 198, C.clay);
    metric(slide, "130/130", "mood dan PHQ-9", 510, 190, 198, C.green);
    metric(slide, "47/47", "kontrak memori", 730, 190, 198, C.amber);
    metric(slide, "27/27", "transisi lifecycle", 950, 190, 198, C.coffee);
    metric(slide, "2/2", "Confession Space", 290, 352, 300, C.green);
    metric(slide, "4/4", "kendali pengguna", 670, 352, 300, C.clay);
    addBox(slide, 70, 518, 1078, 82, { fill: C.greenSoft, line: C.greenSoft, radius: true });
    addText(slide, "Angka ini menguji perilaku yang dikontrak pada skenario otomatis. Mereka tidak menggantikan evaluasi persepsi pengguna nyata, yang tetap direncanakan sebagai tahap lanjutan.", 98, 543, 1020, 34, { size: 16, color: C.coffee, bold: true, align: "center" });
  });

  await add("EVALUASI", "RM1: penilaian buta menghasilkan preferensi yang berimbang, bukan klaim superioritas umum", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "rm1_dialogue_scores.png"), 70, 172, 610, 400, "Median skor rubrik RM1a");
    metric(slide, "18", "skenario satu-giliran", 750, 180, 170, C.coffee);
    metric(slide, "10", "preferensi AXIS", 940, 180, 170, C.green);
    metric(slide, "8", "preferensi baseline", 750, 306, 170, C.clay);
    metric(slide, "6", "dimensi rubrik", 940, 306, 170, C.amber);
    addBox(slide, 730, 462, 405, 92, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "Bukti bersifat indikatif. Keunggulan AXIS tampak pada sebagian konteks bermemori, tetapi tidak membuktikan kualitas percakapan yang lebih baik secara umum.", 756, 486, 352, 48, { size: 13, color: C.coffee, bold: true, align: "center" });
  });

  await add("EVALUASI", "RM1: benchmark keselamatan membaca risiko tersamar, dengan ruang perbaikan yang tetap jelas", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "rm1_safety_metrics.png"), 70, 170, 575, 405, "Metrik benchmark keselamatan");
    metric(slide, "50", "pesan berlabel", 716, 180, 170, C.coffee);
    metric(slide, "0,654", "sensitivitas", 918, 180, 170, C.red);
    metric(slide, "0,917", "spesifisitas", 716, 308, 170, C.green);
    metric(slide, "9", "risiko luput", 918, 308, 170, C.clay);
    addBox(slide, 694, 464, 440, 90, { fill: C.redSoft, line: C.redSoft, radius: true });
    addText(slide, "Sistem dapat menjalankan rute keselamatan pada kasus yang ditangkap, namun belum layak diklaim aman secara umum atau klinis karena masih ada risiko yang luput.", 720, 488, 388, 46, { size: 13, color: C.coffee, bold: true, align: "center" });
  });

  await add("EVALUASI", "RM2: orkestrasi mood dan PHQ-9 tervalidasi sebagai alur percakapan, bukan diagnosis", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "rm2_phq9_metrics.png"), 70, 168, 580, 410, "Metrik pemetaan jawaban bebas PHQ-9");
    metric(slide, "80", "masukan jawaban bebas", 720, 180, 170, C.coffee);
    metric(slide, "73", "jawaban tegas", 920, 180, 170, C.green);
    metric(slide, "1,00", "macro-F1 pada jawaban tegas", 720, 306, 170, C.amber);
    metric(slide, "8/8", "rute item ke-9", 920, 306, 170, C.red);
    addBox(slide, 700, 462, 420, 95, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "Hasil membuktikan pemetaan pada korpus uji terarah dan fidelity alur. Ia bukan validasi psikometrik terhadap pengisian PHQ-9 mandiri oleh manusia.", 725, 486, 370, 50, { size: 13, color: C.coffee, bold: true, align: "center" });
  });

  await add("EVALUASI", "RM3: memori hibrid menjaga kemampuan recall; keunggulan graf dibatasi pada kueri relasional", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "figures", "rm3_ablation_recall.png"), 70, 168, 630, 410, "Recall@5 dan kasus bertarget RM3");
    metric(slide, "15/15", "Recall@5 hibrid", 775, 180, 155, C.green);
    metric(slide, "15/15", "Recall@5 vektor", 950, 180, 155, C.clay);
    metric(slide, "1", "kasus relasional hibrid", 775, 306, 155, C.coffee);
    metric(slide, "0", "kasus relasional vektor", 950, 306, 155, C.red);
    addBox(slide, 746, 462, 388, 94, { fill: C.greenSoft, line: C.greenSoft, radius: true });
    addText(slide, "Hasil belum membuktikan keunggulan statistis knowledge graph untuk semua kueri. Bukti yang lebih kuat ada pada keterhubungan konteks dan kasus kueri yang membutuhkan relasi.", 768, 486, 344, 50, { size: 13, color: C.coffee, bold: true, align: "center" });
  });

  await add("EVALUASI", "Kendali pengguna dan ruang suara sementara hadir sebagai batas pengalaman pendamping", async (slide, ctx) => {
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "app", "08_settings.png"), 86, 182, 252, 360, "Halaman pengaturan AXIS");
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "app", "07_hotlines.png"), 388, 182, 252, 360, "Halaman hotline AXIS");
    await addImageOrPlaceholder(slide, ctx, path.join(assetDir, "app", "04_confession_space.png"), 690, 182, 252, 360, "Confession Space AXIS");
    const textLeft = 980;
    addText(slide, "Kontrol tersedia", textLeft, 195, 180, 24, { size: 18, color: C.coffee, bold: true });
    addText(slide, "• lihat, koreksi, dan hapus memori\n• unduh data dan hapus riwayat\n• hapus akun dan preferensi\n• akses bantuan/hotline", textLeft, 238, 180, 128, { size: 13, color: C.muted });
    addBox(slide, textLeft, 420, 175, 98, { fill: C.greenSoft, line: C.greenSoft, radius: true });
    addText(slide, "Confession Space dikecualikan dari finalisasi memori; keselamatan tetap berjalan pada percakapan sementara.", textLeft + 15, 440, 145, 52, { size: 11, color: C.coffee, bold: true, align: "center" });
  });

  await add("PENUTUP", "AXIS telah direalisasikan sebagai purwarupa yang menghubungkan tiga kebutuhan utama", async (slide) => {
    const results = [
      ["RM1", "Percakapan pendamping", "Kebijakan dialog, pengayaan bahasa, dan guardrail berjalan; kualitas respons dinilai indikatif, bukan superioritas umum.", C.coffee],
      ["RM2", "Asesmen depresi percakapan", "Mood dan PHQ-9 berjalan sebagai skrining bertahap dengan rute keselamatan pada item ke-9.", C.clay],
      ["RM3", "Memori jangka panjang", "Penulisan, lifecycle, dan retrieval hibrid berjalan; manfaat graf paling jelas pada konteks relasional.", C.green],
    ];
    results.forEach(([code, heading, body, accent], index) => {
      const y = 178 + index * 128;
      addBox(slide, 90, y, 1100, 100, { fill: C.white, line: C.line, radius: true });
      addBox(slide, 112, y + 25, 58, 50, { fill: accent, line: accent, radius: true });
      addText(slide, code, 112, y + 40, 58, 20, { size: 15, color: C.white, bold: true, align: "center" });
      addText(slide, heading, 198, y + 18, 400, 22, { size: 18, color: C.ink, bold: true });
      addText(slide, body, 198, y + 50, 920, 34, { size: 14, color: C.muted });
    });
    addBox(slide, 90, 574, 1100, 46, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "Pengujian pengguna nyata tetap merupakan tahap evaluasi lanjutan dan tidak digantikan oleh penilaian otomatis.", 112, 589, 1056, 18, { size: 14, color: C.coffee, bold: true, align: "center" });
  });
}

const figureAssets = {
  "III.1": "solution_use_case.png",
  "III.2": "solution_overview_flow.png",
  "III.3": "cbt_dialogue_flow.png",
  "III.4": "phq9_concept_flow.png",
  "III.5": "memory_concept_flow.png",
  "III.6": "seq_memory_concept.png",
  "III.7": "guardrail_concept_flow.png",
  "IV.1": "system_architecture.png",
  "IV.2": "langgraph_flow.png",
  "IV.3": "seq_chat_turn.png",
  "IV.4": "cbt_dialogue_flow.png",
  "IV.5": "crisis_tier_flow.png",
  "IV.6": "phq9_state_machine.png",
  "IV.7": "kg_schema.png",
  "IV.8": "seq_session_finalize.png",
  "IV.9": "kg_lifecycle.png",
  "IV.10": "context_builder_ranking.png",
  "IV.11": "../app/03_chat_main.png",
  "IV.12": "../app/04_confession_space.png",
  "IV.13": "../app/06_knowledge_graph.png",
  "IV.14": "rm1_dialogue_scores.png",
  "IV.15": "rm1_safety_metrics.png",
  "IV.16": "rm2_phq9_metrics.png",
  "IV.17": "rm3_ablation_recall.png",
  "B.1": "../table-pages/page-132.jpg",
  "C.1": "../app/02_auth_login.png",
  "C.2": "../app/09_profile.png",
  "C.3": "../app/08_settings.png",
  "C.4": "../app/10_help_page.png",
  "C.5": "../app/05_memories_dashboard.png",
  "C.6": "../app/07_hotlines.png",
  "C.7": "neo4j_06_rafid_balanced_subgraph_crop.png",
  "E.1": "rm1_safety_eval_flow.png",
  "E.2": "rm1_dialogue_eval_flow.png",
  "E.3": "rm2_phq9_eval_flow.png",
  "E.4": "rm3_ablation_eval_flow.png",
};

async function addFigureBank(presentation, artifact, figures, slides) {
  const divider = presentation.slides.add();
  const number = presentation.slides.count;
  divider.background.fill = C.coffee;
  addText(divider, "LAMPIRAN PRESENTASI", 82, 150, 760, 22, { size: 13, color: C.amber, bold: true });
  addText(divider, "Bank visual laporan", 82, 194, 780, 70, { size: 48, color: C.white, bold: true });
  addText(divider, "Semua gambar dari laporan utama ditempatkan sebagai objek gambar terpisah agar dapat dipilih, dipindah, dipotong, atau dihapus saat kurasi manual.", 84, 290, 700, 74, { size: 21, color: "#F0DFCF" });
  addText(divider, "Gambar III.1–IV.17 dan gambar lampiran", 84, 596, 620, 22, { size: 14, color: C.amber, bold: true });
  footer(divider, "BANK ARTEFAK", number);
  slides.push(divider);

  for (const entry of figures) {
    const slide = presentation.slides.add();
    const index = presentation.slides.count;
    slideTitle(slide, "BANK ARTEFAK", `Gambar ${entry.id}: ${entry.title}`, index, `Artefak visual dari halaman cetak ${entry.page} pada laporan utama.`);
    const ctx = createSlideContext(artifact, { slideSize: { width: W, height: H }, slideNumber: index, outputDir: __dirname, assetDir, workspaceDir: __dirname });
    const rel = figureAssets[entry.id];
    const asset = rel ? path.resolve(assetDir, "figures", rel) : "";
    await addImageOrPlaceholder(slide, ctx, asset, 95, 176, 1090, 430, `Gambar ${entry.id}: ${entry.title}`);
    addBox(slide, 95, 625, 1090, 38, { fill: C.amberSoft, line: C.amberSoft, radius: true });
    addText(slide, "Catatan kurasi: gambar tersedia sebagai objek PPTX. Pertahankan, potong, atau pindahkan sesuai kebutuhan narasi presentasi.", 118, 636, 1044, 18, { size: 12, color: C.coffee, align: "center" });
    slides.push(slide);
  }
}

async function addTableBank(presentation, artifact, tables, slides) {
  const divider = presentation.slides.add();
  const number = presentation.slides.count;
  divider.background.fill = C.coffee;
  addText(divider, "LAMPIRAN PRESENTASI", 82, 150, 760, 22, { size: 13, color: C.amber, bold: true });
  addText(divider, "Bank tabel laporan", 82, 194, 780, 70, { size: 48, color: C.white, bold: true });
  addText(divider, "Setiap tabel dimasukkan melalui halaman PDF laporan yang memuat tabel tersebut. Halaman menjadi objek gambar yang dapat dipindah atau diganti; isi sumber tetap dapat dirujuk pada `main.tex`.", 84, 290, 720, 86, { size: 21, color: "#F0DFCF" });
  addText(divider, `${tables.length} tabel dari badan laporan dan lampiran`, 84, 596, 620, 22, { size: 14, color: C.amber, bold: true });
  footer(divider, "BANK ARTEFAK", number);
  slides.push(divider);

  for (const entry of tables) {
    const slide = presentation.slides.add();
    const index = presentation.slides.count;
    slideTitle(slide, "BANK ARTEFAK", `Tabel ${entry.id}: ${entry.title}`, index, `Halaman cetak ${entry.page} dari laporan utama. Gambar halaman dibiarkan utuh agar konteks tabel dan caption tetap tersedia.`);
    const ctx = createSlideContext(artifact, { slideSize: { width: W, height: H }, slideNumber: index, outputDir: __dirname, assetDir, workspaceDir: __dirname });
    const pdfPage = entry.page + 17;
    const asset = path.join(assetDir, "table-pages", `page-${String(pdfPage).padStart(3, "0")}.jpg`);
    await addImageOrPlaceholder(slide, ctx, asset, 322, 164, 636, 474, `Tabel ${entry.id}: ${entry.title}`);
    addText(slide, "Objek sumber dapat dikrop pada PowerPoint/Canva bila hanya tabelnya yang ingin dipertahankan.", 190, 654, 900, 18, { size: 11, color: C.muted, align: "center" });
    slides.push(slide);
  }
}

async function main() {
  await ensureArtifactToolWorkspace(__dirname);
  const artifact = await importArtifactTool(__dirname);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  const slides = [];
  const tables = await parseLot(path.join(root, "docs/thesis_latex/main.lot"), "table");
  const figures = await parseLot(path.join(root, "docs/thesis_latex/main.lof"), "figure");

  await addCoreSlides(presentation, artifact, slides);
  await addFigureBank(presentation, artifact, figures, slides);
  await addTableBank(presentation, artifact, tables, slides);

  await fs.mkdir(previewDir, { recursive: true });
  await fs.mkdir(layoutDir, { recursive: true });
  const previewPaths = [];
  for (let i = 0; i < slides.length; i += 1) {
    const preview = await presentation.export({ slide: slides[i], format: "png", scale: 0.6 });
    const previewPath = path.join(previewDir, `slide-${String(i + 1).padStart(3, "0")}.png`);
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
  }
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outPath);
  const manifest = {
    sourceReport: path.join(root, "docs/thesis_latex/main.pdf"),
    sourceDeck: path.join(root, "outputs/manual-20260713-axis-seminar/presentations/axis-seminar-hasil/AXIS_Seminar_Hasil_2026.pptx"),
    sourceReference: path.join(root, "docs/references/PPT_SidangTA_Individu_NextGen_13522110.pdf"),
    output: outPath,
    slideCount: slides.length,
    figureCount: figures.length,
    tableCount: tables.length,
    previews: previewPaths,
  };
  await fs.writeFile(path.join(__dirname, "artifact-build-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  const contactScript = "/Users/ekaaprawira/.codex/plugins/cache/openai-primary-runtime/presentations/26.601.10930/skills/presentations/scripts/make_contact_sheet.py";
  const contactPython = process.env.PYTHON || path.join(root, ".venv", "bin", "python");
  const contact = spawnSync(contactPython, [contactScript, "--output", path.join(__dirname, "qa-contact-sheet.png"), ...previewPaths.slice(0, 20)], { encoding: "utf8" });
  if (contact.status !== 0) throw new Error(contact.stderr || contact.stdout || "Contact sheet generation failed");
  console.log(JSON.stringify(manifest, null, 2));
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exit(1);
});

export const W = 1280;
export const H = 720;
export const C = {
  paper: "#FFFAF4",
  white: "#FFFDF9",
  ink: "#2D2119",
  navy: "#4F3424",
  blue: "#8B5438",
  sky: "#F0DFCF",
  line: "#E5D4C3",
  muted: "#8A7667",
  green: "#7A6049",
  greenSoft: "#EFE6D4",
  amber: "#C8924F",
  amberSoft: "#F9ECD2",
  red: "#A85F5D",
  redSoft: "#F7DDD0",
};

export function box(slide, x, y, w, h, {
  fill = C.white,
  line = C.line,
  radius = false,
  lineWidth = 1,
} = {}) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { width: lineWidth, fill: line },
  });
}

export function text(slide, value, x, y, w, h, {
  size = 18,
  color = C.ink,
  bold = false,
  align = "left",
  font = "Arial",
  fill = "none",
  line = "none",
  inset = 0,
  italic = false,
} = {}) {
  const item = slide.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { width: 0, fill: line },
  });
  item.text.add(value);
  item.text.fontSize = size;
  item.text.color = color;
  item.text.typeface = font;
  item.text.alignment = align;
  item.text.insets = { left: inset, right: inset, top: inset, bottom: inset };
  if (bold) item.text.bold = true;
  if (italic) item.text.italic = true;
  return item;
}

export function line(slide, x1, y1, x2, y2, { color = C.line, width = 1.5 } = {}) {
  return slide.shapes.add({
    geometry: "line",
    position: { left: x1, top: y1, width: x2 - x1, height: y2 - y1 },
    line: { width, fill: color },
  });
}

export function pill(slide, label, x, y, w, {
  fill = C.sky,
  color = C.navy,
  size = 13,
} = {}) {
  box(slide, x, y, w, 28, { fill, line: fill, radius: true });
  text(slide, label, x, y + 5, w, 18, { size, color, bold: true, align: "center" });
}

export function title(slide, section, heading, number) {
  slide.background.fill = C.paper;
  text(slide, section.toUpperCase(), 70, 40, 600, 22, { size: 12, color: C.blue, bold: true });
  text(slide, heading, 70, 68, 1080, 52, { size: 33, color: C.ink, bold: true });
  line(slide, 70, 130, 1210, 130, { color: C.line, width: 1 });
  footer(slide, section, number);
}

export function footer(slide, section, number) {
  const labels = ["MASALAH", "SOLUSI", "IMPLEMENTASI", "EVALUASI"];
  let x = 70;
  labels.forEach((label) => {
    const active = section.toUpperCase().includes(label) ||
      (section.toUpperCase().includes("PENUTUP") && label === "EVALUASI");
    text(slide, label, x, 685, 116, 16, {
      size: 10,
      color: active ? C.navy : C.muted,
      bold: active,
      align: "center",
    });
    line(slide, x, 705, x + 116, 705, { color: active ? C.navy : C.line, width: active ? 3 : 1 });
    x += 128;
  });
  text(slide, String(number).padStart(2, "0"), 1160, 682, 50, 18, { size: 11, color: C.muted, align: "right" });
}

export function numberedCard(slide, n, heading, body, x, y, w, h, color = C.blue) {
  box(slide, x, y, w, h, { fill: C.white, line: C.line, radius: true });
  box(slide, x + 18, y + 18, 34, 34, { fill: color, line: color, radius: true });
  text(slide, n, x + 18, y + 24, 34, 18, { size: 16, color: C.white, bold: true, align: "center" });
  text(slide, heading, x + 66, y + 17, w - 84, 24, { size: 18, bold: true });
  text(slide, body, x + 66, y + 49, w - 84, h - 80, { size: 14, color: C.muted });
}

export function simpleArrow(slide, x, y, label = "") {
  text(slide, "→", x, y, 46, 35, { size: 30, color: C.blue, bold: true, align: "center" });
  if (label) text(slide, label, x - 6, y + 31, 58, 14, { size: 9, color: C.muted, align: "center" });
}

export function miniMetric(slide, value, label, x, y, w, accent = C.navy) {
  box(slide, x, y, w, 104, { fill: C.white, line: C.line, radius: true });
  text(slide, value, x, y + 18, w, 37, { size: 28, color: accent, bold: true, align: "center" });
  text(slide, label, x + 12, y + 63, w - 24, 25, { size: 12, color: C.muted, align: "center" });
}

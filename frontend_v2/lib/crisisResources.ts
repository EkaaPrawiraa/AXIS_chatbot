const LEAD_IN_RE = /(?:ini\s+)?kontak bantuan dari sistem yang bisa kamu hubungi[^\n]*:/i;


export function stripCrisisResourceBlock(content: string): string {
  const lines = content.split('\n');
  const leadInIdx = lines.findIndex((line) => LEAD_IN_RE.test(line.trim()));
  if (leadInIdx === -1) return content;

  let cursor = leadInIdx + 1;
  while (cursor < lines.length && lines[cursor].trim() === '') cursor++;

  const bulletStart = cursor;
  while (cursor < lines.length && lines[cursor].trim().startsWith('-')) cursor++;
  if (cursor === bulletStart) return content;

  while (cursor < lines.length && lines[cursor].trim() === '') cursor++;

  const before = lines.slice(0, leadInIdx).join('\n').trim();
  const after = lines.slice(cursor).join('\n').trim();
  return [before, after].filter(Boolean).join('\n\n');
}

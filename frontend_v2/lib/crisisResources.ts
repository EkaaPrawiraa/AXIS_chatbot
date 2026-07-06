const LEAD_IN_RE = /(?:ini\s+)?kontak bantuan dari sistem yang bisa kamu hubungi[^\n]*:/i;

/**
 * Strips the deterministic hotline resource block (a fixed-format bullet
 * list injected by the agentic crisis guardrail, e.g. "- Healing119.id
 * Hotline: 119 [Call, WhatsApp] (Nasional, Indonesia)") out of a crisis
 * reply's visible text. The dedicated `HotlineWarningCard` + `/hotlines`
 * page are the intended display surface for that contact info — showing it
 * a second time as raw prose inside the chat bubble is redundant and reads
 * as an unstyled data dump.
 *
 * Only strips when the expected shape (lead-in line directly followed by
 * "- " bullet lines) is found; otherwise returns the content untouched so a
 * template change upstream can never silently swallow real message text.
 */
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

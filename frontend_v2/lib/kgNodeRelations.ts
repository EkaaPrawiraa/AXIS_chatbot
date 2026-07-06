import type { MemoryGraphRelation, MemoryNodeType } from '@/models';
import type { RelationEntry } from '@/components/v2/kg/NodeDetailSheet';
import { humanizeSnakeCase } from '@/lib/textFormat';
import { SPOKE_RELATION_LABEL } from '@/components/v2/kg/MemoryMapHub';

// The relations API already returns sourceType/targetType as lowercase
// strings matching our MemoryNodeType directly (e.g. "experience",
// "behaviour") — the one exception is "user" (the User node itself),
// which isn't a memory node type and gets filtered out below.
const VALID_TYPES = new Set<MemoryNodeType>([
  'subject',
  'experience',
  'emotion',
  'trigger',
  'thought',
  'behaviour',
  'topic',
  'memory',
]);

function toNodeType(value: string): MemoryNodeType | null {
  return VALID_TYPES.has(value as MemoryNodeType) ? (value as MemoryNodeType) : null;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

const TYPE_LABELS: Record<MemoryNodeType, string> = {
  subject: 'Subjek',
  experience: 'Pengalaman',
  emotion: 'Perasaan',
  trigger: 'Pemicu',
  thought: 'Pikiran',
  behaviour: 'Perilaku',
  topic: 'Topik',
  memory: 'Memori',
};

/**
 * For a hub node type, find up to 3 OTHER node types it has a real graph
 * relation with, each backed by one genuine connected node's title as the
 * example (not placeholder text) — used to populate NodeDetailSheet's
 * "Relasi utama" list.
 */
export function deriveNodeRelations(type: MemoryNodeType, relations: MemoryGraphRelation[]): RelationEntry[] {
  const seenTypes = new Set<MemoryNodeType>([type]);
  const entries: RelationEntry[] = [];

  for (const relation of relations) {
    const sourceType = toNodeType(relation.sourceType);
    const targetType = toNodeType(relation.targetType);
    const isSource = sourceType === type;
    const isTarget = targetType === type;
    if (!isSource && !isTarget) continue;

    const otherType = isSource ? targetType : sourceType;
    const otherTitle = isSource ? relation.targetTitle : relation.sourceTitle;
    if (!otherType || seenTypes.has(otherType) || !otherTitle) continue;

    seenTypes.add(otherType);
    // Only Topic names come out of the KG as raw snake_case tokens — other
    // node titles (subject names, trigger/thought descriptions) are already
    // natural language and shouldn't be lowercased/reformatted.
    const displayTitle = otherType === 'topic' ? humanizeSnakeCase(otherTitle) : otherTitle;
    // Row title mirrors 22_knowledge_graph_node_detail's "{Verb} {Type}"
    // pattern (e.g. "Dipicu oleh Pemicu") using that type's own connector
    // verb; the description is the user's OWN real connected memory rather
    // than generic canned copy, matching this app's real-data convention.
    const verb = SPOKE_RELATION_LABEL[otherType];
    const title = verb ? `${capitalize(verb)} ${TYPE_LABELS[otherType]}` : TYPE_LABELS[otherType];
    entries.push({
      type: otherType,
      label: relation.label,
      title,
      description: displayTitle.length > 70 ? `${displayTitle.slice(0, 70)}…` : displayTitle,
    });
    if (entries.length >= 3) break;
  }

  return entries;
}

import type { MemoryGraphRelation, MemoryNodeType } from '@/models';
import type { RelationEntry } from '@/components/v2/kg/NodeDetailSheet';
import { humanizeSnakeCase } from '@/lib/textFormat';
import { SPOKE_RELATION_LABEL } from '@/components/v2/kg/MemoryMapHub';


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
  
    const displayTitle = otherType === 'topic' ? humanizeSnakeCase(otherTitle) : otherTitle;
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

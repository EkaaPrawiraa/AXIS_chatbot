import type { MemoryGraphRelation, MemoryNode } from '@/models';
import { isSensitiveNode } from '@/components/v2/memories/MemoryCard';
import { humanizeSnakeCase } from '@/lib/textFormat';

export interface TopicInsight {
  title: string;
  body: string;
  topicId: string;
  conversationId?: string;
}


const CRISIS_TOPIC_KEYWORDS = ['bunuh diri', 'bunuh_diri', 'suicid', 'self_harm', 'self-harm', 'menyakiti diri', 'melukai diri'];

function isCrisisTopicName(name: string): boolean {
  const normalized = name.toLowerCase();
  return CRISIS_TOPIC_KEYWORDS.some((keyword) => normalized.includes(keyword));
}


export function deriveLatestTopicInsight(
  topics: MemoryNode[],
  relations: MemoryGraphRelation[],
  connectedNodesById: Map<string, MemoryNode>
): TopicInsight | null {
  for (const topic of topics) {
    if (isCrisisTopicName(topic.title)) continue;

    const aboutRelations = relations.filter(
      (relation) => relation.label === 'about' && relation.targetId === topic.id && relation.sourceTitle
    );
    let conversationId: string | undefined;
    const hasSensitiveConnection = aboutRelations.some((relation) => {
      const sourceNode = connectedNodesById.get(relation.sourceId);
      if (sourceNode && !conversationId && sourceNode.properties?.conversationId) {
        conversationId = sourceNode.properties.conversationId;
      }
      return sourceNode ? isSensitiveNode(sourceNode) : false;
    });
    if (hasSensitiveConnection) continue;

    return {
      topicId: topic.id,
      title: `Terakhir kamu cerita soal ${humanizeSnakeCase(topic.title)}`,
      body: aboutRelations[0]?.sourceTitle || 'Yuk lanjutkan lagi ceritanya, AXIS masih inget obrolan kita.',
      conversationId,
    };
  }
  return null;
}

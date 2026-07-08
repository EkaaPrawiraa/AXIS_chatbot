'use client';

import { useRouter } from 'next/navigation';
import { Loader2 } from '@/lib/assets';
import { useMemo, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { MobileAppHeader } from '@/components/v2/MobileAppHeader';
import { V2Shell } from '@/components/v2/V2Shell';
import { MemoryMapHub, SPOKE_STYLES, type HubSpoke } from '@/components/v2/kg/MemoryMapHub';
import { NodeDetailSheet } from '@/components/v2/kg/NodeDetailSheet';
import { KnowledgeGraphHeader, SensitiveToggle, ExpandMapButton, LandscapeNotice } from '@/components/v2/kg/KnowledgeGraphUI';
import { knowledgeGraphStyles } from '@/lib/styles/knowledgeGraphStyles';
import { isSensitiveNode } from '@/components/v2/memories/MemoryCard';
import { memoryAPI } from '@/lib/api/memory';
import { NODE_TYPE_DESCRIPTION } from '@/lib/memoryNodeTypes';
import { deriveNodeRelations } from '@/lib/kgNodeRelations';
import type { MemoryNodeType } from '@/models';
import { useQuery } from '@tanstack/react-query';
import { useMemoryRelations } from '@/hooks';
import { useSessionStore } from '@/stores';

// satellite order: top, then clockwise
const HUB_TYPES: Array<{ type: MemoryNodeType; label: string }> = [
  { type: 'experience', label: 'Pengalaman' },
  { type: 'thought', label: 'Pikiran' },
  { type: 'emotion', label: 'Perasaan' },
  { type: 'trigger', label: 'Pemicu' },
  { type: 'behaviour', label: 'Perilaku' },
  { type: 'topic', label: 'Topik' },
  { type: 'memory', label: 'Memori' },
];

export default function KnowledgeGraphPage() {
  return (
    <AuthRequired>
      <KnowledgeGraphContent />
    </AuthRequired>
  );
}

function KnowledgeGraphContent() {
  const router = useRouter();
  const userId = useSessionStore((state) => state.userId);
  const user = useSessionStore((state) => state.user);
  const [hideSensitive, setHideSensitive] = useState(true);
  const [selectedType, setSelectedType] = useState<MemoryNodeType | null>(null);

  const hubQuery = useQuery({
    queryKey: ['memory-hub', userId],
    queryFn: async () => {
      const results = await Promise.all(
        HUB_TYPES.map((item) => memoryAPI.getMemoryNodes(userId!, item.type))
      );
      return HUB_TYPES.map((item, index) => ({
        type: item.type,
        label: item.label,
        total: results[index].total,
        visible: results[index].nodes.filter((node) => !isSensitiveNode(node)).length,
      }));
    },
    enabled: !!userId,
    staleTime: 60_000,
  });

  const relationsQuery = useMemoryRelations(userId);

  const spokes: HubSpoke[] = useMemo(
    () =>
      (hubQuery.data || HUB_TYPES.map((item) => ({ ...item, total: 0, visible: 0 }))).map((item) => ({
        type: item.type,
        label: item.label,
        count: hideSensitive ? item.visible : item.total,
      })),
    [hubQuery.data, hideSensitive]
  );

  const selectedSpoke = spokes.find((spoke) => spoke.type === selectedType);
  const selectedStyle = selectedType ? SPOKE_STYLES[selectedType] : null;
  const selectedRelations = useMemo(
    () => (selectedType ? deriveNodeRelations(selectedType, relationsQuery.data?.relations || []) : []),
    [selectedType, relationsQuery.data]
  );

  const openType = (type: MemoryNodeType) => router.push(`/memories?type=${type}`);

  return (
    <V2Shell showTopbar={false}>
      <main className={knowledgeGraphStyles.mainContainer}>
        <MobileAppHeader />

        <KnowledgeGraphHeader />

        <section className={knowledgeGraphStyles.mapSection}>
          <SensitiveToggle hidden={hideSensitive} onToggle={() => setHideSensitive((value) => !value)} />

          {hubQuery.isLoading ? (
            <div className={knowledgeGraphStyles.loadingContainer}>
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className={knowledgeGraphStyles.hubContainer}>
              <MemoryMapHub
                spokes={spokes}
                userName={user?.displayName || 'Kamu'}
                onSelect={(type) => setSelectedType(type)}
              />
            </div>
          )}

          <ExpandMapButton onClick={() => router.push('/knowledge-graph/expanded')} />
          <LandscapeNotice />
        </section>
      </main>

      {selectedType && selectedStyle ? (
        <NodeDetailSheet
          Icon={selectedStyle.Icon}
          color={selectedStyle.icon}
          bg={selectedStyle.bg}
          label={spokes.find((s) => s.type === selectedType)?.label || selectedType}
          count={selectedSpoke?.count ?? 0}
          description={NODE_TYPE_DESCRIPTION[selectedType] || ''}
          relations={selectedRelations}
          onSelectRelation={(type) => setSelectedType(type)}
          onViewRelations={() => router.push('/knowledge-graph/expanded')}
          onOpenMemories={() => openType(selectedType)}
          onClose={() => setSelectedType(null)}
        />
      ) : null}
    </V2Shell>
  );
}

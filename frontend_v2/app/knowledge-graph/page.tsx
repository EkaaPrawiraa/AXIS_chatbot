'use client';

import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Loader2, MoveDiagonal, Smartphone } from '@/lib/assets';
import { useMemo, useState } from 'react';
import { AuthRequired } from '@/components/session';
import { MobileAppHeader } from '@/components/v2/MobileAppHeader';
import { V2Shell } from '@/components/v2/V2Shell';
import { MemoryMapHub, SPOKE_STYLES, type HubSpoke } from '@/components/v2/kg/MemoryMapHub';
import { NodeDetailSheet } from '@/components/v2/kg/NodeDetailSheet';
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
      <main className="space-y-3.5 pb-6">
        <MobileAppHeader />

        <div>
          <h1 className="text-[25px] font-bold leading-tight text-[var(--v2-ink)]">Peta Memori</h1>
          <p className="mt-1 max-w-[300px] text-[13px] font-medium leading-snug text-[var(--v2-muted)]">
            Ini adalah gambaran hubungan antara memori, pikiran, dan dirimu.
          </p>
        </div>

        <section className="rounded-[24px] border border-[#ece4d3] bg-[#f8f2e7] px-3 pb-4 pt-3">
          <button
            onClick={() => setHideSensitive((value) => !value)}
            className="v2-anim-pressable flex items-center gap-2 rounded-full border border-[#e0d8c5] bg-[#fbf6ec] px-3.5 py-1.5 text-[12px] font-semibold text-[var(--v2-ink)]"
          >
            {hideSensitive ? <EyeOff className="h-[14px] w-[14px]" /> : <Eye className="h-[14px] w-[14px]" />}
            {hideSensitive ? 'Sembunyikan yang sensitif' : 'Tampilkan yang sensitif'}
          </button>

          {hubQuery.isLoading ? (
            <div className="grid h-[336px] place-items-center text-[var(--v2-muted)]">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className="mt-1.5">
              <MemoryMapHub
                spokes={spokes}
                userName={user?.displayName || 'Kamu'}
                onSelect={(type) => setSelectedType(type)}
              />
            </div>
          )}

          <button
            onClick={() => router.push('/knowledge-graph/expanded')}
            className="v2-anim-pressable mx-auto mt-3 flex h-[44px] w-[min(100%,210px)] items-center justify-center gap-2.5 rounded-full bg-[var(--v2-clay)] text-[15.5px] font-bold text-white shadow-[0_14px_26px_-14px_rgba(195,108,69,0.9)]"
          >
            Perbesar peta <MoveDiagonal className="h-[16px] w-[16px]" />
          </button>

          <p className="mt-3 flex items-center justify-center gap-2 text-[12px] font-medium text-[#6f6a5e]">
            <Smartphone className="h-[15px] w-[15px] -rotate-90" />
            Lebih nyaman dilihat saat HP dimiringkan.
          </p>
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

'use client';

import { AppShell } from '@/components/layout';
import { AuthRequired, useRequireAuthRedirect } from '@/components/session';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { memoryAPI } from '@/lib/api/memory';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { MemoryGraphRelation, MemoryNode, MemoryNodeType } from '@/models';
import { useSessionStore } from '@/stores';
import { useQuery } from '@tanstack/react-query';
import {
  GitBranch,
  Layers3,
  Loader2,
  Maximize2,
  Network,
  Orbit,
  Smartphone,
  Sparkles,
  UserRound,
  X,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

const GRAPH_NODE_TYPES: MemoryNodeType[] = [
  'subject',
  'experience',
  'emotion',
  'trigger',
  'thought',
  'behaviour',
  'topic',
  'memory',
];

const SENSITIVE_LEVELS = new Set(['sensitive', 'trauma']);

function isSensitiveNode(node: MemoryNode): boolean {
  const level = node.properties?.sensitivity_level as string | undefined;
  return SENSITIVE_LEVELS.has((level || '').toLowerCase());
}

const TYPE_STYLES: Record<MemoryNodeType, string> = {
  subject: 'border-[#a86632]/50 bg-[#a86632]/13 text-foreground',
  experience: 'border-[#d79b20]/55 bg-[#d79b20]/14 text-foreground',
  emotion: 'border-[#b45f7a]/50 bg-[#b45f7a]/13 text-foreground',
  trigger: 'border-[#c9573b]/50 bg-[#c9573b]/13 text-foreground',
  thought: 'border-[#75563b]/50 bg-[#75563b]/13 text-foreground',
  behaviour: 'border-[#8c8a3f]/50 bg-[#8c8a3f]/13 text-foreground',
  topic: 'border-[#6f8f5a]/50 bg-[#6f8f5a]/13 text-foreground',
  memory: 'border-[#9a4f2f]/50 bg-[#9a4f2f]/13 text-foreground',
};

const TYPE_LINE_COLORS: Record<MemoryNodeType, string> = {
  subject: '#a86632',
  experience: '#d79b20',
  emotion: '#b45f7a',
  trigger: '#c9573b',
  thought: '#75563b',
  behaviour: '#8c8a3f',
  topic: '#6f8f5a',
  memory: '#9a4f2f',
};

type GraphGroup = {
  type: MemoryNodeType;
  nodes: MemoryNode[];
  x: number;
  y: number;
};

type VisibleNodePoint = {
  node: MemoryNode;
  type: MemoryNodeType;
  x: number;
  y: number;
};

type RelationLine = {
  id: string;
  label: string;
  color: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export default function KnowledgeGraphPage() {
  const t = useT();
  const { isInitialized, isAuthenticated } = useRequireAuthRedirect();
  const userId = useSessionStore((state) => state.userId);
  const activeUserId = isAuthenticated ? userId : null;
  const [selectedType, setSelectedType] = useState<MemoryNodeType>('memory');
  const [selectedNodePoint, setSelectedNodePoint] = useState<VisibleNodePoint | null>(null);
  const [showSensitive, setShowSensitive] = useState(false);
  const [graphExpanded, setGraphExpanded] = useState(false);

  const { data: groups = [], isLoading, isError } = useQuery<GraphGroup[]>({
    queryKey: ['knowledge-graph', activeUserId],
    queryFn: async () => {
      if (!activeUserId) throw new Error('User ID is required');
      const responses = await Promise.all(
        GRAPH_NODE_TYPES.map((type) => memoryAPI.getMemoryNodes(activeUserId, type, ''))
      );
      return responses.map((response, index) => {
        const angle = (Math.PI * 2 * index) / GRAPH_NODE_TYPES.length - Math.PI / 2;
        return {
          type: GRAPH_NODE_TYPES[index],
          nodes: response.nodes || [],
          x: 50 + Math.cos(angle) * 33,
          y: 50 + Math.sin(angle) * 33,
        };
      });
    },
    enabled: !!activeUserId,
  });

  const totalNodes = groups.reduce((sum, group) => sum + group.nodes.length, 0);
  const activeGroups = groups.filter((group) => group.nodes.length > 0);
  const selectedGroup = useMemo(
    () => groups.find((group) => group.type === selectedType) || activeGroups[0] || groups[0],
    [activeGroups, groups, selectedType]
  );

  useEffect(() => {
    if (selectedGroup || groups.length === 0) return;
    const firstActive = groups.find((group) => group.nodes.length > 0);
    if (firstActive) setSelectedType(firstActive.type);
  }, [groups, selectedGroup]);

  const { data: relationData, isLoading: isLoadingRelations } = useQuery({
    queryKey: ['knowledge-graph-relations', activeUserId],
    queryFn: async () => {
      if (!activeUserId) throw new Error('User ID is required');
      return memoryAPI.getMemoryRelations(activeUserId, 150);
    },
    enabled: !!activeUserId,
  });

  const relations = relationData?.relations || [];
  const selectedNodeRelations = selectedNodePoint
    ? relations.filter(
        (relation) =>
          relation.sourceId === selectedNodePoint.node.id ||
          relation.targetId === selectedNodePoint.node.id
      )
    : [];

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  if (!userId) {
    return (
      <AppShell>
        <AuthRequired
          title={t('authKnowledgeGraphTitle')}
          description={t('authKnowledgeGraphDescription')}
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="relative">
        <div
          className={cn(
            'axis-page flex min-h-full flex-col gap-6 transition-[filter,opacity,transform] duration-300',
            selectedNodePoint && 'pointer-events-none scale-[0.995] opacity-45 blur-sm'
          )}
        >
          <section className="flex flex-col gap-5 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
          <div>
            {/* <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              {t('memoryStructure')}
            </p> */}
            <h1 className="mt-3 text-4xl font-semibold leading-none tracking-[-0.05em] sm:text-5xl">
              {t('knowledgeGraphTitle')}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
              {t('knowledgeGraphDescription')}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-4 border-t border-border pt-4 md:border-t-0 md:pt-0">
            <div className="flex flex-wrap items-center gap-6">
              <StatPill icon={Layers3} label={t('knowledgeGraphNodes')} value={totalNodes} />
              <StatPill icon={Orbit} label={t('knowledgeGraphCategories')} value={activeGroups.length} />
              <StatPill
                icon={GitBranch}
                label={t('knowledgeGraphRelations')}
                value={relations.length}
              />
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowSensitive((value) => !value)}
              className="bg-card"
            >
              {showSensitive ? t('hideSensitive') : t('showSensitive')}
            </Button>
          </div>
          </section>

          <div>
          <Card className="overflow-hidden p-0">
            {isLoading ? (
              <GraphState
                icon={<Loader2 className="size-5 animate-spin" />}
                title={t('knowledgeGraphLoading')}
                description={t('knowledgeGraphLoadingDescription')}
              />
            ) : isError ? (
              <GraphState
                icon={<Network className="size-5" />}
                title={t('knowledgeGraphUnableTitle')}
                description={t('knowledgeGraphUnableDescription')}
              />
            ) : totalNodes === 0 ? (
              <GraphState
                icon={<Sparkles className="size-5" />}
                title={t('knowledgeGraphEmpty')}
                description={t('knowledgeGraphEmptyDescription')}
              />
            ) : (
              <div className="relative min-h-[min(520px,calc(100dvh-18rem))] touch-pan-x touch-pan-y overflow-hidden bg-[radial-gradient(circle_at_50%_48%,var(--muted)_0,transparent_34%)] sm:min-h-[620px] xl:min-h-[720px]">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setGraphExpanded(true)}
                  className="absolute bottom-4 right-4 z-20 bg-card/92 shadow-[var(--axis-shadow-soft)] backdrop-blur md:hidden"
                >
                  <Maximize2 className="mr-2 size-4" />
                  {t('knowledgeGraphExpandMap')}
                </Button>
                <div className="absolute left-4 top-4 z-10 max-w-[calc(100%-2rem)] rounded-xl border border-border bg-card/88 px-3 py-2 text-xs leading-5 text-muted-foreground shadow-[var(--axis-shadow-soft)] backdrop-blur sm:left-5 sm:top-5">
                  <span className="font-medium text-foreground">
                    {t('knowledgeGraphMap')}
                  </span>
                  <span className="ml-2">
                    {t('knowledgeGraphTapCategory')}
                  </span>
                  <span className="ml-2">
                    {t('knowledgeGraphTapNode')}
                  </span>
                </div>
                <KnowledgeGraphCanvas
                  groups={groups}
                  centerLabel={t('knowledgeGraphCenter')}
                  selectedType={selectedGroup?.type}
                  onSelectType={setSelectedType}
                  onSelectNode={setSelectedNodePoint}
                  relations={relations}
                  userId={userId}
                  showSensitive={showSensitive}
                />
              </div>
            )}
          </Card>
          </div>

          <p className="axis-subtle-panel px-4 py-3 text-sm leading-6 text-muted-foreground">{t('knowledgeGraphHint')}</p>
        </div>

        {graphExpanded && totalNodes > 0 && (
          <div className="fixed inset-0 z-50 flex flex-col bg-background">
            <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border bg-card/95 px-4 py-3 backdrop-blur">
              <div className="min-w-0">
                <p className="text-sm font-semibold">{t('knowledgeGraphExpandedTitle')}</p>
                <p className="mt-1 flex items-center gap-1.5 text-xs leading-5 text-muted-foreground">
                  <Smartphone className="size-3.5 shrink-0" />
                  {t('knowledgeGraphRotateHint')}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setGraphExpanded(false)}
                className="shrink-0 bg-card"
              >
                {t('close')}
              </Button>
            </div>
            <div className="min-h-0 flex-1 overflow-auto bg-[radial-gradient(circle_at_50%_48%,var(--muted)_0,transparent_34%)]">
              <div className="relative h-[calc(100dvh-5rem)] min-h-[620px] w-[980px] max-w-none">
                <KnowledgeGraphCanvas
                  groups={groups}
                  centerLabel={t('knowledgeGraphCenter')}
                  selectedType={selectedGroup?.type}
                  onSelectType={setSelectedType}
                  onSelectNode={(nodePoint) => {
                    setSelectedNodePoint(nodePoint);
                    setGraphExpanded(false);
                  }}
                  relations={relations}
                  userId={userId}
                  showSensitive={showSensitive}
                />
              </div>
            </div>
          </div>
        )}

        {selectedNodePoint && (
          <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-background/55 px-4 py-20 backdrop-blur-md sm:py-24">
            <button
              type="button"
              aria-label={t('closeNodeDetail')}
              className="absolute inset-0 cursor-default"
              onClick={() => setSelectedNodePoint(null)}
            />
            <NodeDetailDialog
              nodePoint={selectedNodePoint}
              relations={selectedNodeRelations}
              isLoadingRelations={isLoadingRelations}
              showSensitive={showSensitive}
              onClose={() => setSelectedNodePoint(null)}
            />
          </div>
        )}
      </div>
    </AppShell>
  );
}

function StatPill({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
}) {
  return (
    <div className="min-w-20">
      <div className="flex items-center gap-2">
        <Icon className="size-3.5 text-primary" />
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      </div>
      <p className="mt-1 text-xl font-semibold tracking-[-0.04em]">{value}</p>
    </div>
  );
}

function GraphState({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-[520px] items-center justify-center p-6 sm:min-h-[620px] xl:min-h-[720px]">
      <div className="max-w-sm text-center">
        <div className="mx-auto flex size-12 items-center justify-center rounded-full border border-border bg-muted/35 text-primary">
          {icon}
        </div>
        <h2 className="mt-4 text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

function KnowledgeGraphCanvas({
  groups,
  centerLabel,
  selectedType,
  onSelectType,
  onSelectNode,
  relations,
  userId,
  showSensitive,
}: {
  groups: GraphGroup[];
  centerLabel: string;
  selectedType?: MemoryNodeType;
  onSelectType: (type: MemoryNodeType) => void;
  onSelectNode: (nodePoint: VisibleNodePoint) => void;
  relations: MemoryGraphRelation[];
  userId: string;
  showSensitive: boolean;
}) {
  const t = useT();
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);
  const typeLabels = getNodeTypeLabels(t);
  const selectedGroup = groups.find((group) => group.type === selectedType);
  const visibleNodePoints: VisibleNodePoint[] = (selectedGroup ? [selectedGroup] : groups).flatMap((group) =>
    getVisibleNodes(group, 4).map((point) => ({ ...point, type: group.type }))
  );
  const relationLines = relations
    .filter((relation) => relationMatchesHover(relation, hoveredKey, userId))
    .map((relation) => getRelationLine(relation, groups, visibleNodePoints, userId))
    .filter((line): line is RelationLine => Boolean(line));

  return (
    <div className="absolute inset-0">
      <svg className="absolute inset-0 h-full w-full text-border" aria-hidden="true">
        <defs>
          <radialGradient id="axis-graph-node-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.2" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="50%" cy="50%" r="32%" fill="url(#axis-graph-node-glow)" opacity="0.22" />
        {relationLines.map((line) => (
          <g key={line.id}>
            <line
              x1={`${line.x1}%`}
              y1={`${line.y1}%`}
              x2={`${line.x2}%`}
              y2={`${line.y2}%`}
              stroke={line.color}
              strokeWidth="1.8"
              opacity="0.86"
            />
            <text
              x={`${(line.x1 + line.x2) / 2}%`}
              y={`${(line.y1 + line.y2) / 2}%`}
              textAnchor="middle"
              className="text-[10px]"
              fill={line.color}
            >
              {line.label}
            </text>
          </g>
        ))}
        {groups.map((group) => (
          <line
            key={`center-${group.type}`}
            x1="50%"
            y1="50%"
            x2={`${group.x}%`}
            y2={`${group.y}%`}
            stroke={TYPE_LINE_COLORS[group.type]}
            strokeWidth="1.25"
            strokeDasharray={group.nodes.length ? '0' : '5 7'}
            opacity={hoveredKey === `type:${group.type}` ? 0.68 : 0}
          />
        ))}
        {groups.flatMap((group) =>
          getVisibleNodes(group).map((nodePoint) => (
            <line
              key={`node-line-${group.type}-${nodePoint.node.id}`}
              x1={`${group.x}%`}
              y1={`${group.y}%`}
              x2={`${nodePoint.x}%`}
              y2={`${nodePoint.y}%`}
              stroke={TYPE_LINE_COLORS[group.type]}
              strokeWidth="1"
              opacity={hoveredKey === `type:${group.type}` ? 0.44 : 0}
            />
          ))
        )}
      </svg>

      <GraphNode
        x={50}
        y={50}
        onMouseEnter={() => setHoveredKey('node:user')}
        onMouseLeave={() => setHoveredKey(null)}
        className="h-24 w-24 border-primary bg-primary text-primary-foreground shadow-[var(--axis-shadow)] sm:h-28 sm:w-28"
      >
        <UserRound className="mb-1 h-5 w-5" />
        <span className="text-sm font-semibold">{centerLabel}</span>
      </GraphNode>

      {groups.map((group) => (
        <GraphNode
          key={group.type}
          x={group.x}
          y={group.y}
          asButton
          onClick={() => onSelectType(group.type)}
          onMouseEnter={() => setHoveredKey(`type:${group.type}`)}
          onMouseLeave={() => setHoveredKey(null)}
          className={cn(
            'h-20 w-20 transition-all duration-300 hover:scale-105 sm:h-24 sm:w-24',
            TYPE_STYLES[group.type],
            selectedType === group.type && 'scale-105 border-primary shadow-[var(--axis-shadow)] ring-4 ring-ring/10',
            selectedType && selectedType !== group.type && 'opacity-55'
          )}
        >
          <span className="text-xs font-semibold">{typeLabels[group.type]}</span>
          <span className="mt-1 text-lg font-bold">{group.nodes.length}</span>
        </GraphNode>
      ))}

      {visibleNodePoints.map((nodePoint) => (
        <GraphNode
          key={`${nodePoint.type}-${nodePoint.node.id}`}
          x={nodePoint.x}
          y={nodePoint.y}
          asButton
          onClick={() => onSelectNode(nodePoint)}
          onMouseEnter={() => setHoveredKey(`node:${nodePoint.node.id}`)}
          onMouseLeave={() => setHoveredKey(null)}
          className={cn(
            'h-14 w-24 px-2 shadow-[var(--axis-shadow-soft)] transition-all duration-300 hover:scale-105 hover:border-ring/40 hover:bg-muted/45 sm:h-16 sm:w-32 sm:px-3',
            TYPE_STYLES[nodePoint.type]
          )}
        >
          <span className="line-clamp-2 text-center text-xs font-medium">
            {graphNodeLabel(t, nodePoint, showSensitive)}
          </span>
        </GraphNode>
      ))}
    </div>
  );
}

function GraphNode({
  x,
  y,
  className,
  children,
  asButton = false,
  onClick,
  onMouseEnter,
  onMouseLeave,
}: {
  x: number;
  y: number;
  className: string;
  children: ReactNode;
  asButton?: boolean;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}) {
  const Component = asButton ? 'button' : 'div';
  return (
    <Component
      type={asButton ? 'button' : undefined}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={cn(
        'absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center rounded-full border text-center backdrop-blur-sm',
        className
      )}
      style={{ left: `${x}%`, top: `${y}%` }}
    >
      {children}
    </Component>
  );
}

function relationMatchesHover(
  relation: MemoryGraphRelation,
  hoveredKey: string | null,
  userId: string
) {
  if (!hoveredKey) return false;
  if (hoveredKey === 'node:user') {
    return relation.sourceId === userId || relation.targetId === userId;
  }
  if (hoveredKey.startsWith('node:')) {
    const nodeId = hoveredKey.slice(5);
    return relation.sourceId === nodeId || relation.targetId === nodeId;
  }
  if (hoveredKey.startsWith('type:')) {
    const type = hoveredKey.slice(5);
    return relation.sourceType === type || relation.targetType === type;
  }
  return false;
}

function getVisibleNodes(group: GraphGroup, limit = 4) {
  const visible = group.nodes.slice(0, limit);
  const radius = limit > 4 ? 15 : 11;
  return visible.map((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(visible.length, 1) - Math.PI / 2;
    return {
      node,
      x: group.x + Math.cos(angle) * radius,
      y: group.y + Math.sin(angle) * radius,
    };
  });
}

function getRelationLine(
  relation: MemoryGraphRelation,
  groups: GraphGroup[],
  visibleNodePoints: VisibleNodePoint[],
  userId: string
): RelationLine | null {
  const sourcePoint = getEndpointPoint(relation.sourceId, relation.sourceType, groups, visibleNodePoints, userId);
  const targetPoint = getEndpointPoint(relation.targetId, relation.targetType, groups, visibleNodePoints, userId);
  if (!sourcePoint || !targetPoint) return null;
  return {
    id: relation.id,
    label: relation.label,
    color: getRelationColor(relation),
    x1: sourcePoint.x,
    y1: sourcePoint.y,
    x2: targetPoint.x,
    y2: targetPoint.y,
  };
}

function getEndpointPoint(
  id: string,
  type: string,
  groups: GraphGroup[],
  visibleNodePoints: VisibleNodePoint[],
  userId: string
) {
  if (type === 'user' || id === userId) {
    return { x: 50, y: 50 };
  }
  const nodePoint = visibleNodePoints.find((point) => point.node.id === id);
  if (nodePoint) {
    return { x: nodePoint.x, y: nodePoint.y };
  }
  const group = groups.find((item) => item.type === type);
  if (group) {
    return { x: group.x, y: group.y };
  }
  return null;
}

function getRelationColor(relation: MemoryGraphRelation) {
  if (relation.sourceType === 'user' && relation.targetType in TYPE_LINE_COLORS) {
    return TYPE_LINE_COLORS[relation.targetType as MemoryNodeType];
  }
  if (relation.sourceType in TYPE_LINE_COLORS) {
    return TYPE_LINE_COLORS[relation.sourceType as MemoryNodeType];
  }
  if (relation.targetType in TYPE_LINE_COLORS) {
    return TYPE_LINE_COLORS[relation.targetType as MemoryNodeType];
  }
  return '#9b7a48';
}

function NodeDetailDialog({
  nodePoint,
  relations,
  isLoadingRelations,
  showSensitive,
  onClose,
}: {
  nodePoint: VisibleNodePoint;
  relations: MemoryGraphRelation[];
  isLoadingRelations: boolean;
  showSensitive: boolean;
  onClose: () => void;
}) {
  const t = useT();
  const node = nodePoint.node;
  const typeLabels = getNodeTypeLabels(t);
  const safeFacts = getSafeNodeFacts(t, nodePoint, relations.length);
  const sensitiveHidden = !showSensitive && isSensitiveNode(nodePoint.node);
  const showPreview =
    !sensitiveHidden && (nodePoint.type === 'topic' || nodePoint.type === 'emotion' || nodePoint.type === 'behaviour');

  return (
    <div className="relative z-10 w-full max-w-3xl overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--axis-shadow)]">
      <div className="relative border-b border-border bg-muted/20 p-5 pr-14 sm:p-6 sm:pr-16">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full"
          aria-label={t('closeNodeDetail')}
        >
          <X className="size-4" />
        </Button>

        <div className="axis-kicker">
          <span className={cn('size-2.5 rounded-full border', TYPE_STYLES[nodePoint.type])} />
          {typeLabels[nodePoint.type]}
        </div>

        <h2 className="mt-4 text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">
          {sensitiveHidden ? t('privateMemoryItem') : node.title || node.id}
        </h2>
        {sensitiveHidden && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            {t('sensitiveContentHidden')}
          </p>
        )}
        {showPreview && node.preview && (
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{node.preview}</p>
        )}
      </div>

      <div className="max-h-[calc(100dvh-18rem)] overflow-y-auto p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {safeFacts.map((fact) => (
            <DetailItem key={fact.label} label={fact.label} value={fact.value} />
          ))}
        </div>

        <section className="mt-6">
          <h3 className="text-sm font-semibold tracking-[-0.01em]">
            {t('visibleRelations')}
          </h3>
          {isLoadingRelations ? (
            <div className="mt-3 rounded-xl border border-dashed border-border bg-muted/20 px-4 py-6 text-center text-sm text-muted-foreground">
              {t('loadingRelations')}
            </div>
          ) : relations.length === 0 ? (
            <div className="mt-3 rounded-xl border border-dashed border-border bg-muted/20 px-4 py-6 text-center text-sm text-muted-foreground">
              {t('noSafeRelationsNode')}
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              {relations.slice(0, 8).map((relation) => (
                <div key={relation.id} className="rounded-xl border border-border bg-muted/20 p-3">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
                    {relation.label}
                  </p>
                  <p className="mt-1 line-clamp-2 text-sm">
                    {relationEndpointLabel(t, relation.sourceType, relation.sourceTitle, showSensitive)} {t('relationTo')}{' '}
                    {relationEndpointLabel(t, relation.targetType, relation.targetTitle, showSensitive)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function graphNodeLabel(
  t: ReturnType<typeof useT>,
  nodePoint: VisibleNodePoint,
  showSensitive: boolean
) {
  if (!showSensitive && isSensitiveNode(nodePoint.node)) {
    return getNodeTypeLabels(t)[nodePoint.type];
  }
  return nodePoint.node.title || nodePoint.node.preview || nodePoint.node.id;
}

function relationEndpointLabel(
  _t: ReturnType<typeof useT>,
  type: string,
  title: string,
  _showSensitive: boolean
) {
  return title || type;
}

function getSafeNodeFacts(
  t: ReturnType<typeof useT>,
  nodePoint: VisibleNodePoint,
  relationCount: number
) {
  const node = nodePoint.node;
  const typeLabels = getNodeTypeLabels(t);
  const facts = [
    {
      label: t('type'),
      value: typeLabels[nodePoint.type],
    },
    {
      label: t('visibility'),
      value: t('safeOverviewOnly'),
    },
  ];

  const category = getStringProperty(node.properties?.category);
  if (category && (nodePoint.type === 'topic' || nodePoint.type === 'trigger' || nodePoint.type === 'behaviour')) {
    facts.push({
      label: t('category'),
      value: category,
    });
  }

  if (node.updatedAt) {
    facts.push({
      label: t('updatedAt'),
      value: new Date(node.updatedAt).toLocaleString(),
    });
  }

  facts.push({
    label: t('safeRelations'),
    value: String(relationCount),
  });

  return facts;
}

function getNodeTypeLabels(t: ReturnType<typeof useT>): Record<MemoryNodeType, string> {
  return {
    subject: t('nodeTypeSubject'),
    experience: t('nodeTypeExperience'),
    emotion: t('nodeTypeEmotion'),
    trigger: t('nodeTypeTrigger'),
    thought: t('nodeTypeThought'),
    behaviour: t('nodeTypeBehaviour'),
    topic: t('nodeTypeTopic'),
    memory: t('nodeTypeMemory'),
  };
}

function getStringProperty(value: unknown) {
  if (typeof value !== 'string') return '';
  return value.trim();
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-muted/20 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-2 break-words text-sm font-medium leading-6">{value}</p>
    </div>
  );
}

'use client';

import { AppShell } from '@/components/layout';
import { AuthRequired, useRequireAuthRedirect } from '@/components/session';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useDeleteMemoryNode, useMemoryNodes, useResetUserMemory, useUpdateMemoryNode } from '@/hooks';
import { useT } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import { MemoryNode, MemoryNodeType } from '@/models';
import { useSessionStore } from '@/stores';
import { AlertTriangle, CheckCircle2, Circle, Eye, EyeOff, Info, Layers2, RotateCcw, Save, Search, Sparkles, Trash2, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

const NODE_TYPES: MemoryNodeType[] = [
  'subject',
  'experience',
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

const SENSITIVE_FIELDS = new Set(['content', 'summary', 'description', 'name', 'aliases']);

export default function MemoriesPage() {
  const t = useT();
  const { isInitialized, isAuthenticated } = useRequireAuthRedirect();
  const userId = useSessionStore((state) => state.userId);
  const activeUserId = isAuthenticated ? userId : null;
  const [nodeType, setNodeType] = useState<MemoryNodeType>('memory');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);
  const [showNodeGuide, setShowNodeGuide] = useState(true);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const { data, isLoading } = useMemoryNodes(activeUserId, nodeType, searchQuery);
  const updateNode = useUpdateMemoryNode();
  const deleteNode = useDeleteMemoryNode();
  const resetMemory = useResetUserMemory();

  const nodes = data?.nodes || [];
  const selected = useMemo(
    () => nodes.find((node) => node.id === selectedId) || null,
    [nodes, selectedId]
  );
  const typeLabels = getNodeTypeLabels(t);
  const typeDescriptions = getNodeTypeDescriptions(t);

  useEffect(() => {
    setSelectedId(null);
  }, [nodeType, searchQuery]);

  useEffect(() => {
    if (!selected) {
      setFormData({});
      return;
    }
    const next: Record<string, any> = {};
    selected.editableFields.forEach((field) => {
      const value = selected.properties[field];
      next[field] = Array.isArray(value) ? value.join(', ') : value ?? '';
    });
    setFormData(next);
  }, [selected]);

  const handleSave = async () => {
    if (!userId || !selected) return;
    await updateNode.mutateAsync({
      userId,
      nodeType,
      nodeId: selected.id,
      request: { properties: formData },
    });
  };

  const handleDelete = async () => {
    if (!userId || !selected) return;
    await deleteNode.mutateAsync({ userId, nodeType, nodeId: selected.id });
    setSelectedId(null);
  };

  const handleResetMemory = async () => {
    if (!userId) return;
    await resetMemory.mutateAsync({ userId });
    setSelectedId(null);
    setIsResetOpen(false);
  };

  if (isInitialized && !isAuthenticated) {
    return null;
  }

  if (!userId) {
    return (
      <AppShell>
        <AuthRequired
          title={t('authMemoriesTitle')}
          description={t('authMemoriesDescription')}
        />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="relative">
        <div
          className={cn(
            'axis-page transition-[filter,opacity,transform] duration-300',
            (selected || isResetOpen) && 'pointer-events-none scale-[0.995] opacity-45 blur-sm'
          )}
        >
          <section className="flex flex-col gap-5 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
            <div>
              {/* <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                {t('memoriesWorkspace')}
              </p> */}
              <h1 className="mt-3 text-4xl font-semibold leading-none tracking-[-0.05em] sm:text-5xl">
                {t('memoriesTitle')}
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
                {t('memoriesWorkspaceDescription')}
              </p>
            </div>

            <div className="flex flex-col gap-4 border-t border-border pt-4 sm:flex-row sm:items-center md:border-t-0 md:pt-0">
              <div className="flex items-center gap-6">
                <CompactStat label={t('category')} value={typeLabels[nodeType]} />
                <CompactStat label={t('records')} value={String(data?.total || 0)} />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowSensitive((value) => !value)}
                className="bg-card"
              >
                {showSensitive ? t('hideSensitive') : t('showSensitive')}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsResetOpen(true)}
                className="bg-card text-destructive hover:text-destructive"
              >
                <RotateCcw className="size-4" />
                {t('resetMemory')}
              </Button>
            </div>
          </section>

          <section className="mt-6">
            <div className="overflow-hidden rounded-xl border border-border bg-card p-4 shadow-[var(--axis-shadow-soft)] sm:p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/35 text-primary">
                    <Info className="size-4" />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold tracking-[-0.01em]">{t('memoryScopeTitle')}</h2>
                    <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{t('memoryScopeDescription')}</p>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setShowNodeGuide((value) => !value)}
                  className="shrink-0 rounded-full border border-border bg-background/70"
                  aria-label={showNodeGuide ? t('hideNodeGuide') : t('showNodeGuide')}
                  title={showNodeGuide ? t('hideNodeGuide') : t('showNodeGuide')}
                >
                  {showNodeGuide ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </Button>
              </div>

              <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {NODE_TYPES.map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setNodeType(type)}
                      className={cn(
                        'shrink-0 rounded-full border px-4 py-2 text-sm transition-[background-color,border-color,color,transform] duration-200 hover:-translate-y-0.5 hover:border-ring/35',
                        nodeType === type
                          ? 'border-primary bg-primary text-primary-foreground'
                          : 'border-border bg-transparent text-muted-foreground hover:bg-muted/45 hover:text-foreground'
                      )}
                    >
                      {typeLabels[type]}
                    </button>
                  ))}
                </div>

                <div className="relative w-full lg:max-w-sm">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder={t('searchMemories')}
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    className="h-11 bg-background/70 pl-10"
                  />
                </div>
              </div>

              {showNodeGuide && (
                <p className="mt-4 rounded-lg border border-border bg-muted/20 px-4 py-3 text-sm leading-6 text-muted-foreground">
                  <span className="font-semibold text-foreground">{typeLabels[nodeType]}.</span>{' '}
                  {typeDescriptions[nodeType]}
                </p>
              )}
            </div>

            <div className="mt-6 overflow-hidden rounded-xl border border-border bg-card shadow-[var(--axis-shadow-soft)]">
              <div className="grid grid-cols-[minmax(0,1fr)_auto] border-b border-border bg-muted/20 px-4 py-3 text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground sm:px-5">
                <span>{t('savedContext')}</span>
                <span>{t('status')}</span>
              </div>

              {isLoading ? (
                <div className="divide-y divide-border">
                  {[0, 1, 2, 3, 4].map((item) => (
                    <div key={item} className="grid gap-3 px-4 py-4 sm:grid-cols-[minmax(0,1fr)_120px] sm:px-5">
                      <div>
                        <div className="h-4 w-52 animate-pulse rounded bg-muted" />
                        <div className="mt-3 h-3 w-4/5 animate-pulse rounded bg-muted" />
                      </div>
                      <div className="h-6 w-20 animate-pulse rounded-full bg-muted sm:justify-self-end" />
                    </div>
                  ))}
                </div>
              ) : nodes.length === 0 ? (
                <EmptyMemoryState
                  title={t('noMemories')}
                  description={
                    t('noMemoriesDescription')
                  }
                />
              ) : (
                <div className="divide-y divide-border">
                  {nodes.map((node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => setSelectedId(node.id)}
                      className="group grid w-full gap-3 px-4 py-4 text-left transition-[background-color] duration-200 hover:bg-muted/35 sm:grid-cols-[minmax(0,1fr)_120px] sm:px-5"
                    >
                      <div className="min-w-0">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border bg-background text-primary">
                            <Layers2 className="size-3.5" />
                          </span>
                          <h2 className="truncate text-sm font-semibold tracking-[-0.01em]">
                            {memoryNodeTitle(t, node, nodeType, showSensitive)}
                          </h2>
                        </div>
                        <p className="mt-2 line-clamp-2 max-w-4xl text-sm leading-6 text-muted-foreground">
                          {memoryNodePreview(t, node, nodeType, showSensitive)}
                        </p>
                        <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                          {node.label}
                        </p>
                      </div>

                      <div className="flex items-start justify-start sm:justify-end">
                        {node.embeddingSynced !== undefined ? (
                          <span
                            className={cn(
                              'inline-flex items-center gap-2 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.1em]',
                              node.embeddingSynced
                                ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                                : 'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                            )}
                          >
                            <span className="size-1.5 rounded-full bg-current" />
                            {node.embeddingSynced ? t('syncedStatus') : t('draftStatus')}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-muted/30 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                            <Circle className="size-2.5" />
                            {t('nodeLabel')}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        {selected && (
          <div className="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-background/55 px-4 py-20 backdrop-blur-md sm:py-24">
            <button
              type="button"
              aria-label={t('closeMemoryEditor')}
              className="absolute inset-0 cursor-default"
              onClick={() => setSelectedId(null)}
            />
            <div className="relative z-10 w-full max-w-3xl overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--axis-shadow)]">
              <NodeEditor
                node={selected}
                nodeType={nodeType}
                formData={formData}
                setFormData={setFormData}
                onSave={handleSave}
                onDelete={handleDelete}
                onClose={() => setSelectedId(null)}
                isSaving={updateNode.isPending}
                isDeleting={deleteNode.isPending}
                showSensitive={showSensitive}
              />
            </div>
          </div>
        )}

        {isResetOpen && (
          <div className="fixed inset-0 z-40 flex items-center justify-center bg-background/55 px-4 py-10 backdrop-blur-md">
            <button
              type="button"
              aria-label={t('resetMemoryCancel')}
              className="absolute inset-0 cursor-default"
              onClick={() => setIsResetOpen(false)}
            />
            <div className="relative z-10 w-full max-w-lg overflow-hidden rounded-2xl border border-border bg-card shadow-[var(--axis-shadow)]">
              <div className="border-b border-border bg-muted/20 p-5 sm:p-6">
                <div className="flex gap-3">
                  <div className="flex size-10 shrink-0 items-center justify-center rounded-full border border-destructive/25 bg-destructive/10 text-destructive">
                    <AlertTriangle className="size-4" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold tracking-[-0.03em]">{t('resetMemoryTitle')}</h2>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{t('resetMemoryDescription')}</p>
                  </div>
                </div>
              </div>
              <div className="p-5 sm:p-6">
                <p className="rounded-xl border border-border bg-muted/20 px-4 py-3 text-sm leading-6 text-muted-foreground">
                  {t('resetMemoryHelp')}
                </p>
                <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsResetOpen(false)}
                    className="bg-card"
                    disabled={resetMemory.isPending}
                  >
                    {t('resetMemoryCancel')}
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={handleResetMemory}
                    disabled={resetMemory.isPending}
                  >
                    <RotateCcw className="size-4" />
                    {resetMemory.isPending ? t('resettingMemory') : t('resetMemoryConfirm')}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function CompactStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tracking-[-0.03em]">{value}</p>
    </div>
  );
}

function EmptyMemoryState({
  title,
  description,
  className,
}: {
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'm-4 flex min-h-56 flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted/20 p-6 text-center',
        className
      )}
    >
      <div className="flex size-11 items-center justify-center rounded-full border border-border bg-card text-primary">
        <Sparkles className="size-4" />
      </div>
      <h3 className="mt-4 text-base font-semibold">{title}</h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  );
}

function NodeEditor({
  node,
  nodeType,
  formData,
  setFormData,
  onSave,
  onDelete,
  onClose,
  isSaving,
  isDeleting,
  showSensitive,
}: {
  node: MemoryNode;
  nodeType: MemoryNodeType;
  formData: Record<string, any>;
  setFormData: (data: Record<string, any>) => void;
  onSave: () => void;
  onDelete: () => void;
  onClose: () => void;
  isSaving: boolean;
  isDeleting: boolean;
  showSensitive: boolean;
}) {
  const t = useT();
  const sensitiveHidden = !showSensitive && isSensitiveNode(node);
  const visibleFields = sensitiveHidden
    ? node.editableFields.filter((field) => !SENSITIVE_FIELDS.has(field))
    : node.editableFields;

  return (
    <div className="flex max-h-[calc(100dvh-8rem)] flex-col">
      <div className="relative border-b border-border bg-muted/20 p-5 pr-14 sm:p-6 sm:pr-16">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full"
          aria-label={t('closeMemoryEditor')}
        >
          <X className="size-4" />
        </Button>

        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="min-w-0">
            <div className="axis-kicker">
              <CheckCircle2 className="size-3.5" />
              {node.label}
            </div>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">
              {sensitiveHidden ? t('privateMemoryItem') : node.title || node.id}
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {getNodeTypeDescriptions(t)[nodeType]}
            </p>
            <p className="mt-2 line-clamp-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              {sensitiveHidden ? t('sensitiveContentHidden') : node.preview || t('noPreviewYet')}
            </p>
          </div>
          {node.embeddingSynced !== undefined && (
            <span
              className={cn(
                'inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium',
                node.embeddingSynced
                  ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  : 'border-amber-500/25 bg-amber-500/10 text-amber-700 dark:text-amber-300'
              )}
            >
              <span className="size-1.5 rounded-full bg-current" />
              {node.embeddingSynced ? t('syncedContext') : t('pendingSync')}
            </span>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5 sm:p-6">
        {sensitiveHidden && (
          <div className="mb-5 rounded-xl border border-border bg-muted/20 px-4 py-3 text-sm leading-6 text-muted-foreground">
            {t('sensitiveContentHelp')}
          </div>
        )}
        <div className="grid gap-4">
          {visibleFields.map((field) => {
            const enumValues = node.enumFields?.[field];
            return (
              <div key={field}>
                <Label htmlFor={field} className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  {getFieldLabel(t, field)}
                </Label>
                {enumValues?.length ? (
                  <select
                    id={field}
                    value={formData[field] || ''}
                    onChange={(event) => setFormData({ ...formData, [field]: event.target.value })}
                    className="axis-field-select mt-2"
                  >
                    {enumValues.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                ) : field === 'summary' || field === 'description' || field === 'content' ? (
                  <textarea
                    id={field}
                    value={formData[field] || ''}
                    onChange={(event) => setFormData({ ...formData, [field]: event.target.value })}
                    rows={5}
                    className="mt-2 min-h-36 w-full rounded-lg border border-input bg-background/60 px-3 py-2 text-sm leading-6 outline-none transition-[border-color,box-shadow,background-color] focus:border-ring focus:bg-card focus:ring-4 focus:ring-ring/10"
                  />
                ) : (
                  <Input
                    id={field}
                    value={formData[field] || ''}
                    onChange={(event) => setFormData({ ...formData, [field]: event.target.value })}
                    className="mt-2 bg-background/60"
                  />
                )}
                {field === 'aliases' && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t('aliasesHelp')}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex flex-col-reverse gap-3 border-t border-border bg-muted/15 p-5 sm:flex-row sm:items-center sm:justify-end sm:p-6">
        <Button variant="outline" onClick={onDelete} disabled={isDeleting} className="text-destructive hover:text-destructive sm:mr-auto">
          <Trash2 className="mr-2 h-4 w-4" />
          {isDeleting ? t('deleting') : t('delete')}
        </Button>
        <Button onClick={onSave} disabled={isSaving || sensitiveHidden} className="shadow-[var(--axis-shadow-soft)]">
          <Save className="mr-2 h-4 w-4" />
          {isSaving ? t('saving') : t('saveChanges')}
        </Button>
      </div>
    </div>
  );
}

function memoryNodeTitle(
  t: ReturnType<typeof useT>,
  node: MemoryNode,
  nodeType: MemoryNodeType,
  showSensitive: boolean
) {
  if (!showSensitive && isSensitiveNode(node)) {
    return `${getNodeTypeLabels(t)[nodeType]} ${node.id.slice(0, 6)}`;
  }
  return node.title || node.id;
}

function memoryNodePreview(
  t: ReturnType<typeof useT>,
  node: MemoryNode,
  nodeType: MemoryNodeType,
  showSensitive: boolean
) {
  if (!showSensitive && isSensitiveNode(node)) {
    return t('sensitiveHiddenPreview');
  }
  return node.preview || t('noPreviewAvailable');
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

function getNodeTypeDescriptions(t: ReturnType<typeof useT>): Record<MemoryNodeType, string> {
  return {
    subject: t('nodeTypeSubjectDescription'),
    experience: t('nodeTypeExperienceDescription'),
    emotion: t('nodeTypeEmotionDescription'),
    trigger: t('nodeTypeTriggerDescription'),
    thought: t('nodeTypeThoughtDescription'),
    behaviour: t('nodeTypeBehaviourDescription'),
    topic: t('nodeTypeTopicDescription'),
    memory: t('nodeTypeMemoryDescription'),
  };
}

function getFieldLabel(t: ReturnType<typeof useT>, field: string) {
  const labels: Record<string, string> = {
    description: t('fieldDescription'),
    label: t('fieldLabel'),
    category: t('fieldCategory'),
    aliases: t('fieldAliases'),
    content: t('fieldContent'),
    name: t('fieldName'),
    role: t('fieldRole'),
    summary: t('fieldSummary'),
  };
  return labels[field] || field;
}

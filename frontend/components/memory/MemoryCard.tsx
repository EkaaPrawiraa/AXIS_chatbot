'use client';

import { Memory } from '@/models';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Trash2, Pin } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useT } from '@/lib/i18n';
import { usePreferencesStore } from '@/stores';
import { enUS, id as idLocale } from 'date-fns/locale';

interface MemoryCardProps {
  memory: Memory;
  onPin?: (memoryId: string, isPinned: boolean) => void;
  onDelete?: (memoryId: string) => void;
}

export function MemoryCard({ memory, onPin, onDelete }: MemoryCardProps) {
  const t = useT();
  const language = usePreferencesStore((state) => state.language);

  return (
    <Card className="group p-4 transition-[background-color,border-color,transform] duration-200 hover:-translate-y-0.5 hover:border-ring/35 hover:bg-muted/35">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="font-semibold mb-1">{memory.title}</h3>
          <p className="text-sm text-muted-foreground line-clamp-2 mb-3">{memory.content}</p>
          <div className="flex items-center gap-2 flex-wrap">
            {memory.tags.map((tag) => (
              <span
                key={tag}
                className="rounded-md border border-border bg-accent/25 px-2 py-1 font-mono text-[11px] uppercase tracking-[0.08em] text-accent-foreground"
              >
                {tag}
              </span>
            ))}
            <span className="text-xs text-muted-foreground">
              {formatDistanceToNow(memory.createdAt, {
                addSuffix: true,
                locale: language === 'en' ? enUS : idLocale,
              })}
            </span>
          </div>
        </div>

        <div className="flex flex-shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
          {onPin && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onPin(memory.id, !memory.isPinned)}
              className="h-8 w-8 p-0"
              title={memory.isPinned ? t('unpinMemory') : t('pinMemory')}
            >
              <Pin className={`w-3 h-3 ${memory.isPinned ? 'fill-current' : ''}`} />
            </Button>
          )}
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(memory.id)}
              className="h-8 w-8 p-0 text-destructive hover:text-destructive"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

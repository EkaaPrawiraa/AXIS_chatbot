import { BaseEntity, ID } from './common';

export type MemoryTag = 'important' | 'goal' | 'challenge' | 'achievement' | 'relationship' | 'health' | 'work' | 'personal' | 'custom';

export interface Memory extends BaseEntity {
  userId: ID;
  content: string;
  title: string;
  tags: MemoryTag[];
  isPinned: boolean;
  source?: 'chat' | 'reflection' | 'manual';
  relatedConversationId?: ID;
  emotion?: string;
}

export interface CreateMemoryRequest {
  title: string;
  content: string;
  tags?: MemoryTag[];
  relatedConversationId?: ID;
}

export interface UpdateMemoryRequest {
  title?: string;
  content?: string;
  tags?: MemoryTag[];
  isPinned?: boolean;
}

export interface MemoryFilter {
  tags?: MemoryTag[];
  startDate?: number;
  endDate?: number;
  searchQuery?: string;
}

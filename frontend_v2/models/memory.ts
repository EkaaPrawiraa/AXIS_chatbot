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

export type MemoryNodeType =
  | 'subject'
  | 'experience'
  | 'emotion'
  | 'trigger'
  | 'thought'
  | 'behaviour'
  | 'topic'
  | 'memory';

export interface MemoryNode {
  id: ID;
  type: MemoryNodeType;
  label: string;
  title: string;
  preview: string;
  properties: Record<string, any>;
  editableFields: string[];
  enumFields: Record<string, string[]>;
  embeddingSynced?: boolean;
  updatedAt?: string;
}

export interface MemoryNodeListResponse {
  nodes: MemoryNode[];
  nodeType: MemoryNodeType;
  total: number;
}

export interface MemoryGraphRelation {
  id: ID;
  sourceId: ID;
  sourceType: string;
  sourceTitle: string;
  targetId: ID;
  targetType: string;
  targetTitle: string;
  relationType: string;
  label: string;
  confidence?: number;
}

export interface MemoryGraphRelationListResponse {
  relations: MemoryGraphRelation[];
  total: number;
}

export interface UpdateMemoryNodeRequest {
  properties: Record<string, any>;
}

export interface MemoryResetResponse {
  reset: boolean;
  nodesDeleted: number;
  sessionsDeleted: number;
  userRelationshipsDeleted: number;
  pgvectorRowsDeleted: number;
  userDeleted: number;
}

export interface MemoryPurgeResponse {
  purged: boolean;
  nodesDeleted: number;
  sessionsDeleted: number;
  userDeleted: number;
  pgvectorRowsDeleted: number;
}

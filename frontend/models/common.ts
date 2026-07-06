export type ID = string;
export type Timestamp = number; // Unix milliseconds

export interface BaseEntity {
  id: ID;
  createdAt: Timestamp;
  updatedAt: Timestamp;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface ErrorDetail {
  code: string;
  message: string;
  field?: string;
}

export type Emotion =
  | 'happy'
  | 'sad'
  | 'anxious'
  | 'calm'
  | 'angry'
  | 'confused'
  | 'grateful'
  | 'hopeful'
  | 'lonely'
  | 'overwhelmed'
  | 'peaceful'
  | 'frustrated';

export const EMOTIONS: Record<Emotion, string> = {
  happy: 'Happy',
  sad: 'Sad',
  anxious: 'Anxious',
  calm: 'Calm',
  angry: 'Angry',
  confused: 'Confused',
  grateful: 'Grateful',
  hopeful: 'Hopeful',
  lonely: 'Lonely',
  overwhelmed: 'Overwhelmed',
  peaceful: 'Peaceful',
  frustrated: 'Frustrated',
};

import { create } from 'zustand';

interface MessageLimitState {
  limit: number | null;
  remaining: number | null;
  setFromHeaders: (headers: Record<string, unknown> | Headers) => void;
}

function readHeader(headers: Record<string, unknown> | Headers, key: string): string | null {
  if (headers instanceof Headers) return headers.get(key);
  const value = headers[key.toLowerCase()];
  return typeof value === 'string' ? value : null;
}

// mirrors the gateway's X-RateLimit-*-MessagesDaily headers so the composer can show "N/100 pesan hari ini"
export const useMessageLimitStore = create<MessageLimitState>((set) => ({
  limit: null,
  remaining: null,
  setFromHeaders: (headers) => {
    const limit = readHeader(headers, 'x-ratelimit-limit-messagesdaily');
    const remaining = readHeader(headers, 'x-ratelimit-remaining-messagesdaily');
    if (limit === null || remaining === null) return;
    set({ limit: Number(limit), remaining: Number(remaining) });
  },
}));

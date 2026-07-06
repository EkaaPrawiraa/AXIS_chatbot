import { apiClient } from './client';
import { APP_CONFIG } from '../config';
import { Conversation, Message, SendMessageRequest, SendMessageResponse, ID, ChatStreamEvent } from '@/models';
import { API_ROUTES } from '../constants';

export const chatAPI = {
  getConversations: async (userId: ID) => {
    const response = await apiClient.get<Conversation[]>(API_ROUTES.CONVERSATIONS, {
      params: { userId },
    });
    return response.data.data || [];
  },

  createConversation: async (userId: ID, title: string) => {
    const response = await apiClient.post<Conversation>(API_ROUTES.CONVERSATIONS, {
      userId,
      title,
    });
    return response.data.data!;
  },

  getMessages: async (conversationId: ID, page: number = 1, pageSize: number = 50, userId?: string) => {
    const url = API_ROUTES.MESSAGES.replace(':id', conversationId);
    const response = await apiClient.get<Message[]>(url, {
      params: { page, pageSize, ...(userId ? { userId } : {}) },
    });
    return response.data.data || [];
  },

  sendMessage: async (request: SendMessageRequest) => {
    const url = API_ROUTES.SEND_MESSAGE.replace(':id', request.conversationId);
    const response = await apiClient.post<SendMessageResponse>(url, {
      userId: request.userId,
      content: request.content,
      voiceUrl: request.voiceUrl,
      voice: request.voice,
      language_pref: request.language_pref,
      preferred_response_model: request.preferred_response_model,
      phq9_state: request.phq9_state,
      cbt_state: request.cbt_state,
    });
    return response.data.data!;
  },

  streamMessage: async (
    request: SendMessageRequest,
    onEvent: (event: ChatStreamEvent) => void
  ): Promise<SendMessageResponse> => {
    const url = `${APP_CONFIG.api.baseUrl}${API_ROUTES.STREAM_MESSAGE.replace(':id', request.conversationId)}`;
    const csrfToken = readCookie('axis_csrf');
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      body: JSON.stringify({
        userId: request.userId,
        content: request.content,
        language_pref: request.language_pref,
        preferred_response_model: request.preferred_response_model,
        phq9_state: request.phq9_state,
        cbt_state: request.cbt_state,
        voice: request.voice,
      }),
    });
    if (!response.ok || !response.body) {
      throw new Error(`stream message failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let donePayload: SendMessageResponse | null = null;

    const consumeBlock = (block: string) => {
      const lines = block.split(/\r?\n/);
      let event = 'message';
      const data: string[] = [];
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        if (line.startsWith('data:')) {
          const value = line.slice(5);
          data.push(value.startsWith(' ') ? value.slice(1) : value);
        }
      }
      const payload = data.join('\n');
      if (!payload) return;
      if (event === 'token') {
        onEvent({ event: 'token', data: payload });
        return;
      }
      if (event === 'done') {
        donePayload = JSON.parse(payload) as SendMessageResponse;
        onEvent({ event: 'done', data: donePayload });
        return;
      }
      if (event === 'error') {
        onEvent({ event: 'error', data: payload });
        throw new Error(payload);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || '';
      for (const block of blocks) consumeBlock(block);
    }
    buffer += decoder.decode();
    if (buffer.trim()) consumeBlock(buffer);
    const finalPayload = donePayload as SendMessageResponse | null;
    if (!finalPayload) throw new Error('stream ended without final response');
    return finalPayload;
  },

  deleteConversation: async (conversationId: ID) => {
    const response = await apiClient.delete(
      API_ROUTES.CONVERSATIONS + `/${conversationId}`
    );
    return response.data.success;
  },

  updateConversationTitle: async (conversationId: ID, title: string) => {
    const response = await apiClient.patch<Conversation>(
      API_ROUTES.CONVERSATIONS + `/${conversationId}`,
      { title }
    );
    return response.data.data!;
  },
};

function readCookie(name: string): string {
  if (typeof document === 'undefined') return '';
  const prefix = `${name}=`;
  const value = document.cookie
    .split('; ')
    .find((part) => part.startsWith(prefix))
    ?.slice(prefix.length);
  return value ? decodeURIComponent(value) : '';
}

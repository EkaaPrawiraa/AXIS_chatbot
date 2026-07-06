import { apiClient } from './client';
import { Conversation, Message, SendMessageRequest, ID } from '@/models';
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

  getMessages: async (conversationId: ID, page: number = 1, pageSize: number = 50) => {
    const url = API_ROUTES.MESSAGES.replace(':id', conversationId);
    const response = await apiClient.get<Message[]>(url, {
      params: { page, pageSize },
    });
    return response.data.data || [];
  },

  sendMessage: async (request: SendMessageRequest) => {
    const url = API_ROUTES.SEND_MESSAGE.replace(':id', request.conversationId);
    const response = await apiClient.post(url, request);
    return response.data.data;
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

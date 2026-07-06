import { wsClient } from './client';
import { WS_EVENTS } from '../constants';
import { ChatStreamEvent, ID } from '@/models';

type ChatStreamHandler = (event: ChatStreamEvent) => void;

export const chatSocket = {
  onStreamStart(handler: (messageId: ID) => void) {
    return wsClient.on(WS_EVENTS.CHAT_STREAM_START, handler);
  },

  onStreamChunk(handler: (data: { messageId: ID; content: string }) => void) {
    return wsClient.on(WS_EVENTS.CHAT_STREAM_CHUNK, handler);
  },

  onStreamEnd(handler: (messageId: ID) => void) {
    return wsClient.on(WS_EVENTS.CHAT_STREAM_END, handler);
  },
  async sendMessageAndStream(conversationId: ID, content: string): Promise<string> {
    return new Promise((resolve, reject) => {
      let fullContent = '';
      
      const unsubscribeStart = this.onStreamStart((messageId) => {
        console.log('[ChatSocket] Stream started:', messageId);
      });

      const unsubscribeChunk = this.onStreamChunk(({ content: chunk }) => {
        fullContent += chunk;
      });

      const unsubscribeEnd = this.onStreamEnd(() => {
        unsubscribeStart();
        unsubscribeChunk();
        unsubscribeEnd();
        resolve(fullContent);
      });
      wsClient.send(WS_EVENTS.CHAT_MESSAGE, {
        conversationId,
        content,
        timestamp: Date.now(),
      });
      setTimeout(() => {
        unsubscribeStart();
        unsubscribeChunk();
        unsubscribeEnd();
        reject(new Error('Chat stream timeout'));
      }, 60000);
    });
  },
  offAll() {
    wsClient.off(WS_EVENTS.CHAT_STREAM_START);
    wsClient.off(WS_EVENTS.CHAT_STREAM_CHUNK);
    wsClient.off(WS_EVENTS.CHAT_STREAM_END);
  },
};

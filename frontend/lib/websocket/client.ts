import { APP_CONFIG } from '../config';
import { WS_EVENTS } from '../constants';

type EventHandler = (data: any) => void;
type MessageListener = {
  event: string;
  handler: EventHandler;
};

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners: MessageListener[] = [];
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private isIntentionallyClosed = false;

  constructor() {
    this.url = APP_CONFIG.websocket.url;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.isIntentionallyClosed = false;
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.emit(WS_EVENTS.CONNECT, {});
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.emit(WS_EVENTS.ERROR, { error });
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[WebSocket] Closed');
          this.stopHeartbeat();
          
          if (!this.isIntentionallyClosed) {
            this.attemptReconnect();
          }
          this.emit(WS_EVENTS.DISCONNECT, {});
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: { event: string; data?: any }) {
    const { event, data } = message;
    this.listeners
      .filter((listener) => listener.event === event)
      .forEach((listener) => {
        try {
          listener.handler(data);
        } catch (error) {
          console.error(`[WebSocket] Error in listener for ${event}:`, error);
        }
      });
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= APP_CONFIG.websocket.reconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = APP_CONFIG.websocket.reconnectDelay * this.reconnectAttempts;
    
    console.log(
      `[WebSocket] Attempting to reconnect (${this.reconnectAttempts}/${APP_CONFIG.websocket.reconnectAttempts}) in ${delay}ms`
    );

    this.reconnectTimeout = setTimeout(() => {
      this.emit(WS_EVENTS.RECONNECT, {});
      this.connect().catch((error) => {
        console.error('[WebSocket] Reconnection failed:', error);
      });
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send('heartbeat', {});
      }
    }, APP_CONFIG.websocket.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  on(event: string, handler: EventHandler) {
    this.listeners.push({ event, handler });
    
    return () => {
      this.listeners = this.listeners.filter(
        (listener) => !(listener.event === event && listener.handler === handler)
      );
    };
  }

  off(event: string, handler?: EventHandler) {
    if (handler) {
      this.listeners = this.listeners.filter(
        (listener) => !(listener.event === event && listener.handler === handler)
      );
    } else {
      this.listeners = this.listeners.filter((listener) => listener.event !== event);
    }
  }

  send(event: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, data }));
    } else {
      console.warn('[WebSocket] Not connected, cannot send:', event);
    }
  }

  private emit(event: string, data: any) {
    this.handleMessage({ event, data });
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  disconnect() {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.listeners = [];
  }
}
export const wsClient = new WebSocketClient();

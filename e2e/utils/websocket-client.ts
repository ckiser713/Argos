/**
 * WebSocket Client for E2E Testing
 * 
 * Provides a WebSocket client wrapper for testing real-time features
 */

export interface WebSocketEvent {
  type: string;
  data: any;
  timestamp: number;
}

export class WebSocketTestClient {
  private ws: WebSocket | null = null;
  private events: WebSocketEvent[] = [];
  private connected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;

  constructor(
    private url: string,
    private onMessage?: (event: WebSocketEvent) => void,
    private onError?: (error: Event) => void,
    private onClose?: () => void
  ) {}

  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.connected = true;
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const wsEvent: WebSocketEvent = {
              type: data.type || 'message',
              data: data.data || data,
              timestamp: Date.now(),
            };
            this.events.push(wsEvent);
            if (this.onMessage) {
              this.onMessage(wsEvent);
            }
          } catch (e) {
            // Handle non-JSON messages
            const wsEvent: WebSocketEvent = {
              type: 'message',
              data: event.data,
              timestamp: Date.now(),
            };
            this.events.push(wsEvent);
            if (this.onMessage) {
              this.onMessage(wsEvent);
            }
          }
        };

        this.ws.onerror = (error) => {
          if (this.onError) {
            this.onError(error);
          }
          reject(error);
        };

        this.ws.onclose = () => {
          this.connected = false;
          if (this.onClose) {
            this.onClose();
          }
          // Auto-reconnect logic
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
              this.connect().catch(() => {
                // Reconnection failed, will retry
              });
            }, this.reconnectDelay);
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Send message to WebSocket server
   */
  send(data: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
  }

  /**
   * Subscribe to specific event types
   */
  subscribe(eventType: string, callback: (event: WebSocketEvent) => void): void {
    this.onMessage = (event) => {
      if (event.type === eventType) {
        callback(event);
      }
    };
  }

  /**
   * Wait for specific event type
   */
  async waitForEvent(eventType: string, timeout: number = 10000): Promise<WebSocketEvent> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Timeout waiting for event type: ${eventType}`));
      }, timeout);

      const checkEvents = () => {
        const event = this.events.find((e) => e.type === eventType);
        if (event) {
          clearTimeout(timer);
          resolve(event);
        } else {
          setTimeout(checkEvents, 100);
        }
      };

      checkEvents();
    });
  }

  /**
   * Get all events of specific type
   */
  getEventsByType(eventType: string): WebSocketEvent[] {
    return this.events.filter((e) => e.type === eventType);
  }

  /**
   * Get all events
   */
  getAllEvents(): WebSocketEvent[] {
    return [...this.events];
  }

  /**
   * Clear event history
   */
  clearEvents(): void {
    this.events = [];
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }

  /**
   * Get connection state
   */
  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}

/**
 * Helper function to create WebSocket client in Playwright context
 */
export async function createWebSocketClient(
  page: any,
  url: string,
  onMessage?: (event: WebSocketEvent) => void
): Promise<WebSocketTestClient> {
  // Use Playwright's WebSocket support
  const wsUrl = url.replace('http://', 'ws://').replace('https://', 'wss://');
  
  // Create client using page context
  const client = new WebSocketTestClient(wsUrl, onMessage);
  await client.connect();
  
  return client;
}


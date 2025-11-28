/**
 * Hook for real-time agent run streaming via WebSocket.
 * Connects to backend streaming endpoints and provides live updates.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import type { AgentRun, AgentStep, AgentMessage, AgentNodeState } from "../domain/types";

export interface AgentStreamEvent {
  type: string;
  timestamp: string;
  run?: AgentRun;
  step?: AgentStep;
  message?: AgentMessage;
  nodeState?: AgentNodeState;
  errorMessage?: string;
}

export interface UseAgentStreamOptions {
  projectId: string;
  runId?: string;
  enabled?: boolean;
  onEvent?: (event: AgentStreamEvent) => void;
}

export function useAgentStream(options: UseAgentStreamOptions) {
  const { projectId, runId, enabled = true, onEvent } = options;
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!enabled || !projectId) {
      return;
    }

    // Determine WebSocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = runId
      ? `${protocol}//${host}/api/stream/projects/${projectId}/agent-runs/${runId}`
      : `${protocol}//${host}/api/stream/projects/${projectId}/agent-runs`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        console.log("Agent stream connected");
      };

      ws.onmessage = (event) => {
        try {
          const data: AgentStreamEvent = JSON.parse(event.data);
          setEvents((prev) => [...prev, data]);
          onEvent?.(data);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onerror = (event) => {
        console.error("WebSocket error:", event);
        setError(new Error("WebSocket connection error"));
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts && enabled) {
          reconnectAttempts.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 1000 * reconnectAttempts.current); // Exponential backoff
        }
      };
    } catch (e) {
      setError(e instanceof Error ? e : new Error("Failed to create WebSocket"));
      setIsConnected(false);
    }
  }, [projectId, runId, enabled, onEvent]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (enabled && projectId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, projectId, runId, connect, disconnect]);

  return {
    isConnected,
    events,
    error,
    connect,
    disconnect,
    clearEvents: () => setEvents([]),
  };
}


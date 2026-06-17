"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";

interface WebSocketMessage {
  type: string;
  data: unknown;
  timestamp: string;
}

type MessageHandler = (message: WebSocketMessage) => void;

interface UseRealtimeOptions {
  onMessage?: MessageHandler;
  onEvent?: (eventType: string, data: unknown) => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnects?: number;
}

export function useRealtime(
  path: string,
  options: UseRealtimeOptions = {}
) {
  const {
    onMessage,
    onEvent,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnects = 10,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const token = useAuthStore((state) => state.token);

  const connect = useCallback(() => {
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${window.location.host}`;
    const url = `${host}/ws/${path}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      reconnectCountRef.current = 0;
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (autoReconnect && reconnectCountRef.current < maxReconnects) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectCountRef.current++;
          connect();
        }, reconnectInterval);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);
        onMessage?.(message);
        onEvent?.(message.type, message.data);
      } catch {
        // Ignore malformed messages
      }
    };
  }, [path, token, autoReconnect, reconnectInterval, maxReconnects, onMessage, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsConnected(false);
  }, []);

  return {
    isConnected,
    lastMessage,
    send,
    disconnect,
    reconnect: connect,
  };
}

export function useTwinRealtime(customerId: string) {
  const { lastMessage, isConnected } = useRealtime(`twins/${customerId}`, {
    onEvent: (type, _data) => {
      if (type === "twin_update") {
        // Twin updated
      }
    },
  });

  return { lastMessage, isConnected };
}

export function useSimulationRealtime(simulationId: string) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>("");

  useRealtime(`simulations/${simulationId}`, {
    onEvent: (type, data) => {
      if (type === "simulation_progress") {
        setProgress((data as { progress: number }).progress);
      }
      if (type === "simulation_status") {
        setStatus((data as { status: string }).status);
      }
    },
  });

  return { progress, status };
}

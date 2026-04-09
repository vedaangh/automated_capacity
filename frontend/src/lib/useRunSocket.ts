"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSEvent, RunResponse } from "./api";
import { wsUrl } from "./api";

export type ConnectionState = "connecting" | "open" | "closed" | "error";

export interface UseRunSocketReturn {
  connectionState: ConnectionState;
  lastEvent: WSEvent | null;
  send: (msg: string) => void;
  close: () => void;
}

/**
 * Opens a WebSocket to /runs/{runId}/stream.
 * Calls `onEvent` for every parsed WSEvent.
 * Automatically reconnects on disconnect (up to 5 retries).
 */
export function useRunSocket(
  runId: string | null,
  onEvent: (event: WSEvent) => void,
): UseRunSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const retriesRef = useRef(0);
  const maxRetries = 5;

  const [connectionState, setConnectionState] = useState<ConnectionState>("closed");
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);

  const connect = useCallback(() => {
    if (!runId) return;

    const url = wsUrl(runId);
    setConnectionState("connecting");

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState("open");
      retriesRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as WSEvent;
        setLastEvent(event);
        onEventRef.current(event);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = () => {
      setConnectionState("error");
    };

    ws.onclose = () => {
      setConnectionState("closed");
      wsRef.current = null;

      // Auto-reconnect with backoff
      if (retriesRef.current < maxRetries) {
        const delay = Math.min(1000 * 2 ** retriesRef.current, 10000);
        retriesRef.current += 1;
        setTimeout(connect, delay);
      }
    };
  }, [runId]);

  useEffect(() => {
    connect();
    return () => {
      retriesRef.current = maxRetries; // prevent reconnect on unmount
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const send = useCallback((msg: string) => {
    wsRef.current?.send(msg);
  }, []);

  const close = useCallback(() => {
    retriesRef.current = maxRetries;
    wsRef.current?.close();
  }, []);

  return { connectionState, lastEvent, send, close };
}

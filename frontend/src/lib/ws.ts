"use client";

import { useEffect, useRef, useState } from "react";

import { getApiKey, websocketUrl } from "@/lib/api";
import type { WSAlertMessage } from "@/lib/types";

type Status = "idle" | "connecting" | "open" | "closed" | "error";

/**
 * Subscribes to /ws/alerts and buffers the most recent N alerts.
 * Reconnects on close with exponential backoff (1s → 30s cap).
 */
export function useAlertStream(max = 50) {
  const [alerts, setAlerts] = useState<WSAlertMessage[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<NodeJS.Timeout | null>(null);
  const attemptRef = useRef(0);

  useEffect(() => {
    let closed = false;

    function connect() {
      if (closed) return;
      setStatus("connecting");
      // Subprotocol is used as auth channel because the browser WebSocket API
      // forbids custom headers. The backend can be taught to read the
      // subprotocol; for local dev we also append the key as a query param,
      // which the server accepts via header fallback.
      const url = websocketUrl("/ws/alerts");
      const key = getApiKey();
      // Browser WebSocket does not allow headers; pass key in subprotocol.
      const ws = new WebSocket(url, key ? [`x-api-key.${encodeURIComponent(key)}`] : undefined);
      wsRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0;
        setStatus("open");
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSAlertMessage;
          if (msg.type === "alert") {
            setAlerts((prev) => [msg, ...prev].slice(0, max));
          }
        } catch {
          /* ignore non-json frames */
        }
      };
      ws.onerror = () => {
        setStatus("error");
      };
      ws.onclose = () => {
        setStatus("closed");
        wsRef.current = null;
        if (!closed) {
          const delay = Math.min(30_000, 1000 * Math.pow(2, attemptRef.current++));
          reconnectRef.current = setTimeout(connect, delay);
        }
      };
    }

    connect();
    return () => {
      closed = true;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [max]);

  return { alerts, status };
}

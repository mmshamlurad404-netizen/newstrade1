import { useEffect, useRef, useState } from "react";

import { wsUrl } from "../api/client";

export function useWebSocket<T>(path: string, max = 50) {
  const [items, setItems] = useState<T[]>([]);
  const [connected, setConnected] = useState(false);
  const retry = useRef(1000);
  const socket = useRef<WebSocket | null>(null);
  const closed = useRef(false);

  useEffect(() => {
    closed.current = false;

    const connect = () => {
      const ws = new WebSocket(wsUrl(path));
      socket.current = ws;
      ws.onopen = () => {
        setConnected(true);
        retry.current = 1000;
      };
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "ping") {
          return;
        }
        setItems((prev) => [message.data as T, ...prev].slice(0, max));
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed.current) {
          return;
        }
        retry.current = Math.min(retry.current * 2, 30000);
        setTimeout(connect, retry.current);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed.current = true;
      socket.current?.close();
    };
  }, [path, max]);

  return { items, connected };
}

import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "../services/supabase";

interface ProcessingEvent {
  type: "processing_status";
  document_id: string;
  status: string;
  progress: number;
  message: string;
  timestamp: string;
}

type WSStatus = "connecting" | "connected" | "disconnected" | "error";

export function useWebSocket(onEvent?: (event: ProcessingEvent) => void) {
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(async () => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}`;
    const url = `${wsHost}/ws/processing?token=${session.access_token}`;

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "ping") return; // heartbeat
        if (data.type === "processing_status" && onEvent) {
          onEvent(data as ProcessingEvent);
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      // Auto-reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => setStatus("error");
  }, [onEvent]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
    setStatus("disconnected");
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { status, disconnect, reconnect: connect };
}

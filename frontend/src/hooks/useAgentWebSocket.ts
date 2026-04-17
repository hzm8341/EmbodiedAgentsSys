import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentMessage, ExecuteTaskRequest } from "../types";

const DEFAULT_WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/agent/ws`;

export function useAgentWebSocket(url: string = DEFAULT_WS_URL) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<AgentMessage[]>([]);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onerror = () => setIsConnected(false);
    ws.onmessage = (evt) => {
      try {
        const msg: AgentMessage = JSON.parse(evt.data);
        setMessages((prev) => [...prev, msg]);
      } catch (e) {
        console.error("invalid message", evt.data, e);
      }
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const executeTask = useCallback(
    (task: string, observationState: Record<string, number>, scenario?: string, maxSteps = 3) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.warn("WebSocket not open");
        return;
      }
      const payload: ExecuteTaskRequest = {
        type: "execute_task",
        task,
        scenario,
        observation: { state: observationState },
        max_steps: maxSteps,
      };
      wsRef.current.send(JSON.stringify(payload));
    },
    []
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { isConnected, messages, executeTask, clearMessages };
}

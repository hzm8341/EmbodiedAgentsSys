import { useCallback, useEffect, useRef, useState } from 'react'
import { useStatusStore } from '../store/useStatusStore'
import type { AgentMessage, ExecuteTaskRequest } from '../types'

export function useAgentWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const { setConnectionStatus, setRobotStatus } = useStatusStore()

  useEffect(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws
    setConnectionStatus('connecting')

    ws.onopen = () => {
      setIsConnected(true)
      setConnectionStatus('connected')
    }
    ws.onclose = () => {
      setIsConnected(false)
      setConnectionStatus('disconnected')
      setRobotStatus('idle')
    }
    ws.onerror = () => {
      setIsConnected(false)
      setConnectionStatus('disconnected')
    }
    ws.onmessage = (evt) => {
      try {
        const msg: AgentMessage = JSON.parse(evt.data)
        setMessages((prev) => [...prev, msg])
        if (msg.type === 'execution') setRobotStatus('working')
        if (msg.type === 'result' || msg.type === 'error') setRobotStatus('idle')
      } catch (e) {
        console.error('invalid ws message', e)
      }
    }

    return () => ws.close()
  }, [url, setConnectionStatus, setRobotStatus])

  const executeTask = useCallback(
    (task: string, observationState: Record<string, number>, scenario?: string, maxSteps = 3) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
      const payload: ExecuteTaskRequest = {
        type: 'execute_task',
        task,
        scenario,
        observation: { state: observationState },
        max_steps: maxSteps,
      }
      wsRef.current.send(JSON.stringify(payload))
    },
    []
  )

  const resetToHome = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'reset_to_home' }))
  }, [])

  const clearMessages = useCallback(() => setMessages([]), [])

  return { isConnected, messages, executeTask, resetToHome, clearMessages }
}

import { useCallback, useEffect, useRef, useState } from 'react'
import { useStatusStore } from '../store/useStatusStore'
import { useSyncStore } from '../store/useSyncStore'
import type { AgentMessage, ExecuteTaskRequest } from '../types'

export function useAgentWebSocket(url: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<AgentMessage[]>([])
  const { setConnectionStatus, setRobotStatus } = useStatusStore()
  const { setCurrentTask, setReasoningAction, commitExecution, clearSync, setExecutionState } = useSyncStore()

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
        const body = (msg.payload ?? msg.data ?? {}) as any
        if (msg.type === 'task_start') {
          const task = String(body.task ?? '')
          setCurrentTask(task)
        }
        if (msg.type === 'reasoning') {
          const step = Number(body.step ?? msg.step ?? -1)
          const action = String(body.action?.action ?? '')
          const arm = String(body.action?.params?.arm ?? '')
          const x = Number(body.action?.params?.x)
          const y = Number(body.action?.params?.y)
          const z = Number(body.action?.params?.z)
          const target = Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z) ? [x, y, z] as [number, number, number] : null
          setReasoningAction(step, action, arm, target)
        }
        if (msg.type === 'execution') {
          const fb = body.feedback as any
          const targetRaw = fb?.result_data?.target
          const actualRaw = fb?.result_data?.actual
          const target = Array.isArray(targetRaw) && targetRaw.length === 3 ? [Number(targetRaw[0]), Number(targetRaw[1]), Number(targetRaw[2])] as [number, number, number] : undefined
          const actual = Array.isArray(actualRaw) && actualRaw.length === 3 ? [Number(actualRaw[0]), Number(actualRaw[1]), Number(actualRaw[2])] as [number, number, number] : undefined
          commitExecution({
            step: Number(body.step ?? msg.step ?? fb?.step ?? -1),
            action: String(fb?.action ?? ''),
            arm: fb?.params?.arm ? String(fb.params.arm) : undefined,
            target,
            actual,
            success: Boolean(fb?.success),
            timestamp: Number(msg.timestamp ?? Date.now() / 1000),
          })
        }
        if (msg.type === 'execution_status') {
          const state = String(body.state ?? 'idle')
          if (state === 'running' || state === 'paused' || state === 'aborted' || state === 'completed') {
            setExecutionState(state)
          } else {
            setExecutionState('idle')
          }
          if (state === 'paused') setRobotStatus('paused')
          if (state === 'aborted') setRobotStatus('aborted')
        }
        if (msg.type === 'execution_control') {
          const state = String(body.state ?? '')
          if (state === 'paused' || state === 'running' || state === 'aborted') {
            setExecutionState(state as 'paused' | 'running' | 'aborted')
          }
        }
        if (msg.type === 'approval_required') {
          setExecutionState('paused')
          setRobotStatus('paused')
        }
        if (msg.type === 'execution') setRobotStatus('working')
        if (msg.type === 'result' || msg.type === 'error') setRobotStatus('idle')
      } catch (e) {
        console.error('invalid ws message', e)
      }
    }

    return () => ws.close()
  }, [url, setConnectionStatus, setExecutionState, setRobotStatus])

  const executeTask = useCallback(
    (task: string, observationState: Record<string, number>, scenario?: string, maxSteps?: number) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
      const payload: ExecuteTaskRequest = {
        type: 'execute_task',
        task,
        scenario,
        observation: { state: observationState },
      }
      if (maxSteps !== undefined) payload.max_steps = maxSteps
      wsRef.current.send(JSON.stringify(payload))
    },
    []
  )

  const resetToHome = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'reset_to_home' }))
  }, [])

  const pauseTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'pause_task' }))
  }, [])

  const resumeTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'resume_task' }))
  }, [])

  const stepTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'step_task' }))
  }, [])

  const abortTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'abort_task' }))
  }, [])

  const approveTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'approve_task' }))
  }, [])

  const rejectTask = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'reject_task' }))
  }, [])

  const clearAll = useCallback(() => {
    setMessages([])
    clearSync()
  }, [clearSync])

  return {
    isConnected,
    messages,
    executeTask,
    resetToHome,
    pauseTask,
    resumeTask,
    stepTask,
    abortTask,
    approveTask,
    rejectTask,
    clearMessages: clearAll,
  }
}

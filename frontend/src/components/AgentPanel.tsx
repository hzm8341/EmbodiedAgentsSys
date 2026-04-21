import { useEffect, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'
import { useAgentWebSocket } from '../hooks/useAgentWebSocket'
import type { AgentMessage, Scenario } from '../types'

// ── 工具函数 ────────────────────────────────────────────────────────────────
function findLast(msgs: AgentMessage[], type: AgentMessage['type']) {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].type === type) return msgs[i]
  }
  return null
}
function countByType(msgs: AgentMessage[], type: AgentMessage['type']) {
  return msgs.filter((m) => m.type === type).length
}

// ── LayerCard ───────────────────────────────────────────────────────────────
const ACCENT: Record<string, string> = {
  planning:  'border-purple-400',
  reasoning: 'border-blue-400',
  execution: 'border-amber-400',
  learning:  'border-green-400',
}

function LayerCard({
  title, layerKey, messages,
}: {
  title: string; layerKey: AgentMessage['type']; messages: AgentMessage[]
}) {
  const msg = findLast(messages, layerKey)
  const count = countByType(messages, layerKey)
  const active = !!msg
  return (
    <div className={`border-2 rounded-lg p-3 transition-colors
      ${active ? `bg-white ${ACCENT[layerKey] ?? 'border-gray-300'}` : 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-gray-700">{title}</span>
        {count > 0 && (
          <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded-full font-semibold">×{count}</span>
        )}
      </div>
      {msg ? (
        <pre className="text-xs font-mono bg-gray-100 rounded p-2 max-h-32 overflow-auto whitespace-pre-wrap break-all">
          {JSON.stringify(msg.data, null, 2)}
        </pre>
      ) : (
        <span className="text-xs text-gray-400 italic">Waiting...</span>
      )}
    </div>
  )
}

// ── AgentPanel ──────────────────────────────────────────────────────────────
export const AgentPanel = () => {
  const { websocketUrl } = useSettingsStore()
  const { isConnected, messages, executeTask, resetToHome, clearMessages } =
    useAgentWebSocket(websocketUrl)

  const [task, setTask] = useState('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [showLog, setShowLog] = useState(false)

  useEffect(() => {
    fetch('/api/agent/scenarios')
      .then((r) => r.json())
      .then(setScenarios)
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (messages.some((m) => m.type === 'result' || m.type === 'error')) {
      setIsExecuting(false)
    }
  }, [messages])

  const handleExecute = () => {
    if (!task.trim()) return
    clearMessages()
    setIsExecuting(true)
    executeTask(task, { gripper_open: 1.0 }, selected ?? undefined, 3)
  }

  const handleReset = () => {
    setTask('')
    setSelected(null)
    clearMessages()
    setIsExecuting(false)
  }

  const result = messages.find((m) => m.type === 'result')
  const errors = messages.filter((m) => m.type === 'error')
  const taskStart = messages.find((m) => m.type === 'task_start')
  const success = (result?.data?.task_success as boolean | undefined) ?? false

  return (
    <div className="flex gap-4 h-full">
      {/* 左列 */}
      <div className="w-72 shrink-0 flex flex-col gap-4">
        {/* 连接状态 */}
        <div className="bg-white rounded-xl border border-gray-200 p-3 flex items-center gap-2 text-sm">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-400'}`} />
          <span className="text-gray-600">
            Agent WS: {isConnected ? '已连接' : '未连接'}
          </span>
        </div>

        {/* Task Input */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-col gap-3">
          <h3 className="text-sm font-bold text-gray-800">任务输入</h3>
          <textarea
            rows={3}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="e.g., Pick up the red cube"
            disabled={isExecuting}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
          />

          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">预设场景</p>
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {scenarios.length === 0 && (
                <p className="text-xs text-gray-400">加载中...</p>
              )}
              {scenarios.map((sc) => (
                <button
                  key={sc.name}
                  onClick={() => { setSelected(sc.name); setTask(sc.task) }}
                  disabled={isExecuting}
                  className={`w-full text-left px-3 py-2 rounded-lg border text-xs transition-colors
                    ${selected === sc.name
                      ? 'bg-blue-50 border-blue-400 text-blue-800'
                      : 'bg-gray-50 border-gray-200 hover:border-blue-300 hover:bg-blue-50'}`}
                >
                  <div className="font-semibold">{sc.name}</div>
                  <div className="text-gray-400 mt-0.5">{sc.description}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleExecute}
              disabled={isExecuting || !task.trim()}
              className="flex-1 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExecuting ? '执行中...' : 'Execute'}
            </button>
            <button
              onClick={handleReset}
              disabled={isExecuting}
              className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-semibold hover:bg-gray-300 disabled:opacity-50"
            >
              Reset
            </button>
            <button
              onClick={resetToHome}
              disabled={isExecuting}
              title="机器人回零"
              className="px-3 py-2 bg-amber-400 text-white rounded-lg text-sm font-semibold hover:bg-amber-500 disabled:opacity-50"
            >
              Home
            </button>
          </div>
        </div>

        {/* Observation */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h3 className="text-sm font-bold text-gray-800 mb-3">Robot Observation</h3>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Current Task:</span>
              <span className="font-medium text-gray-800 max-w-[60%] text-right truncate">
                {(taskStart?.data?.task as string) ?? '(none)'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Messages:</span>
              <span className="font-medium">{messages.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Layers:</span>
              <span className="font-medium text-right max-w-[60%]">
                {Array.from(new Set(messages.map((m) => m.type))).join(', ') || '(none)'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 右列 */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Execution Monitor */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-800">Execution Monitor</h3>
            {isExecuting && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-semibold animate-pulse">
                Running
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <LayerCard title="Planning Layer"   layerKey="planning"  messages={messages} />
            <LayerCard title="Reasoning Layer"  layerKey="reasoning" messages={messages} />
            <LayerCard title="Execution"        layerKey="execution" messages={messages} />
            <LayerCard title="Learning Layer"   layerKey="learning"  messages={messages} />
          </div>
        </div>

        {/* Result */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-800">Execution Results</h3>
            <button
              onClick={() => setShowLog((v) => !v)}
              className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
            >
              {showLog ? 'Hide Log' : 'Show Log'}
            </button>
          </div>

          {!result && errors.length === 0 ? (
            <p className="text-xs text-gray-400">执行任务后查看结果。</p>
          ) : (
            <>
              {result && (
                <>
                  <div className={`inline-block text-xs font-bold px-3 py-1 rounded-lg mb-2
                    ${success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {success ? '✓ Task Success' : '✗ Task Failed'}
                  </div>
                  <pre className="text-xs font-mono bg-gray-100 rounded-lg p-3 max-h-40 overflow-auto whitespace-pre-wrap break-all">
                    {JSON.stringify(result.data, null, 2)}
                  </pre>
                </>
              )}
              {errors.length > 0 && (
                <div className="mt-2 bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-xs font-bold text-red-700 mb-1">Errors:</p>
                  {errors.map((e, i) => (
                    <p key={i} className="text-xs text-red-600">
                      {(e.data as { message?: string })?.message}
                    </p>
                  ))}
                </div>
              )}
            </>
          )}

          {showLog && (
            <div className="mt-3 bg-gray-900 rounded-lg p-3 max-h-40 overflow-auto">
              {messages.map((m, i) => (
                <div key={i} className="text-xs font-mono text-gray-300 py-0.5">
                  <span className="text-amber-400 font-semibold">[{m.type}]</span>{' '}
                  {m.timestamp ? new Date(m.timestamp * 1000).toLocaleTimeString() : ''}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

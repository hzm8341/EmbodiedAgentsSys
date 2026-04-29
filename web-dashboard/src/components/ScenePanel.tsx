import { useEffect, useRef, useState } from 'react'
import {
  getSceneView,
  listBackends,
  selectBackend,
  type BackendDescriptor,
  type SceneSnapshot,
} from '../services/runtime'
import { useStatusStore } from '../store/useStatusStore'

interface DetectedObject {
  id: string
  label: string
  confidence: number
}

interface SceneResult {
  scene_description: string
  objects: DetectedObject[]
  raw: string
}

export const ScenePanel = () => {
  const imgRef = useRef<HTMLImageElement>(null)
  const { selectedBackend, setSelectedBackend, sceneConnected, setSceneConnected } = useStatusStore()
  const [backends, setBackends] = useState<BackendDescriptor[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<SceneResult | null>(null)
  const [error, setError] = useState('')
  const [backendError, setBackendError] = useState('')
  const [liveScene, setLiveScene] = useState<SceneSnapshot | null>(null)
  const streamIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const connectSceneStream = (backendId: string) => {
    wsRef.current?.close()
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(
      `${protocol}://${window.location.host}/api/agent/ws?backend=${encodeURIComponent(backendId)}&event=scene_snapshot`
    )
    wsRef.current = ws

    ws.onopen = () => {
      setSceneConnected(true)
    }
    ws.onclose = () => {
      setSceneConnected(false)
    }
    ws.onerror = () => {
      setSceneConnected(false)
    }
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type?: string
          data?: SceneSnapshot
          backend?: string
        }
        if (payload.type === 'scene_snapshot' && payload.data) {
          setLiveScene(payload.data)
          setSelectedBackend(payload.backend ?? payload.data.backend)
        }
      } catch {
        // ignore malformed message
      }
    }
  }

  useEffect(() => {
    let cancelled = false
    if (!selectedBackend) return

    const tick = async () => {
      try {
        const scene = await getSceneView()
        if (cancelled) return
        setLiveScene(scene)
        setSceneConnected(true)
      } catch {
        if (cancelled) return
        setSceneConnected(false)
      }
    }

    tick()
    const timer = setInterval(tick, 500)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [selectedBackend, setSceneConnected])

  useEffect(() => {
    let cancelled = false

    const loadBackends = async () => {
      try {
        const data = await listBackends()
        if (cancelled) return
        setBackends(data.backends)
        setSelectedBackend(data.selected_backend)
        await getSceneView().then((scene) => setLiveScene(scene))
        connectSceneStream(data.selected_backend)
        setBackendError('')
      } catch (e) {
        if (cancelled) return
        setSceneConnected(false)
        setBackendError(String(e))
      }
    }

    loadBackends()

    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [setSceneConnected, setSelectedBackend])

  const handleBackendChange = async (backendId: string) => {
    setBackendError('')
    try {
      const data = await selectBackend(backendId)
      setSelectedBackend(data.selected_backend)
      await getSceneView().then((scene) => setLiveScene(scene))
      connectSceneStream(data.selected_backend)
    } catch (e) {
      setSceneConnected(false)
      setBackendError(String(e))
    }
  }

  const startStream = () => {
    setIsStreaming(true)
    const tick = async () => {
      try {
        const resp = await fetch('/api/camera/frame')
        const data = await resp.json()
        if (data.frame && imgRef.current) {
          imgRef.current.src = `data:image/jpeg;base64,${data.frame}`
        }
      } catch {
        // ignore
      }
    }
    tick()
    streamIntervalRef.current = setInterval(tick, 100) // ~10fps
  }

  const stopStream = () => {
    setIsStreaming(false)
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current)
      streamIntervalRef.current = null
    }
  }

  const analyzeScene = async () => {
    setIsAnalyzing(true)
    setError('')
    try {
      const resp = await fetch('/api/scene/describe', { method: 'POST' })
      const data = await resp.json()
      if (data.error) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="flex gap-4 h-full">
      {/* 左侧：摄像头画面 */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex-1 bg-black rounded-lg overflow-hidden flex items-center justify-center min-h-64">
          <img
            ref={imgRef}
            className="max-h-full max-w-full"
            alt="camera"
            style={{ display: isStreaming ? 'block' : 'none' }}
          />
          {!isStreaming && (
            <p className="text-gray-400">点击「开始预览」查看实时画面</p>
          )}
        </div>
        <div className="mt-3 flex gap-3">
          <button
            onClick={isStreaming ? stopStream : startStream}
            className={`px-4 py-2 rounded text-white text-sm ${
              isStreaming ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'
            }`}
          >
            {isStreaming ? '停止预览' : '开始预览'}
          </button>
          <button
            onClick={analyzeScene}
            disabled={isAnalyzing}
            className="px-4 py-2 rounded bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white text-sm"
          >
            {isAnalyzing ? '分析中...' : '场景分析'}
          </button>
        </div>
      </div>

      {/* 右侧：分析结果 */}
      <div className="w-80 flex flex-col gap-4 shrink-0">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between gap-3 mb-2">
            <h3 className="text-sm font-semibold text-gray-300">数据源</h3>
            <span className={`h-2.5 w-2.5 rounded-full ${sceneConnected ? 'bg-green-400' : 'bg-red-400'}`} />
          </div>
          <select
            value={selectedBackend}
            onChange={(event) => handleBackendChange(event.target.value)}
            className="w-full rounded bg-gray-900 border border-gray-700 px-3 py-2 text-sm text-gray-100"
          >
            {backends.length === 0 ? (
              <option value={selectedBackend}>{selectedBackend}</option>
            ) : (
              backends.map((backend) => (
                <option key={backend.backend_id} value={backend.backend_id}>
                  {backend.display_name}
                </option>
              ))
            )}
          </select>
          {backendError && (
            <p className="mt-2 text-xs text-red-400">{backendError}</p>
          )}
          {liveScene && (
            <p className="mt-2 text-xs text-gray-400">
              机器人 {liveScene.robots.length} 台，物体 {liveScene.objects.length} 个
            </p>
          )}
        </div>

        {/* 场景描述 */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">场景描述</h3>
          {error ? (
            <p className="text-red-400 text-sm">{error}</p>
          ) : result?.scene_description ? (
            <p className="text-gray-100 text-sm leading-relaxed">{result.scene_description}</p>
          ) : (
            <p className="text-gray-500 text-sm">点击「场景分析」获取描述</p>
          )}
        </div>

        {/* 目标检测 */}
        <div className="bg-gray-800 rounded-lg p-4 flex-1">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">检测到的物体</h3>
          {result && result.objects.length > 0 ? (
            <ul className="space-y-2">
              {result.objects.map((obj) => (
                <li key={obj.id} className="flex items-center justify-between">
                  <span className="text-gray-100 text-sm">{obj.label}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      obj.confidence >= 0.8
                        ? 'bg-green-700 text-green-200'
                        : obj.confidence >= 0.6
                        ? 'bg-yellow-700 text-yellow-200'
                        : 'bg-red-800 text-red-200'
                    }`}
                  >
                    {(obj.confidence * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-sm">
              {result ? '未检测到物体' : '暂无结果'}
            </p>
          )}
        </div>

        {/* 原始输出（折叠） */}
        {result?.raw && (
          <details className="bg-gray-800 rounded-lg p-3">
            <summary className="text-xs text-gray-400 cursor-pointer">模型原始输出</summary>
            <pre className="mt-2 text-xs text-gray-300 whitespace-pre-wrap">{result.raw}</pre>
          </details>
        )}
      </div>
    </div>
  )
}

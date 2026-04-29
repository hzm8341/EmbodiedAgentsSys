import { useRef, useState } from 'react'

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
  const [isStreaming, setIsStreaming] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<SceneResult | null>(null)
  const [error, setError] = useState('')
  const streamIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

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

import { useEffect, useRef, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'
import { useStatusStore } from '../store/useStatusStore'

export const CameraPanel = () => {
  const imgRef = useRef<HTMLImageElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState('')
  const { apiUrl, refreshRate } = useSettingsStore()
  const { setFps } = useStatusStore()

  useEffect(() => {
    if (!isStreaming) return

    const fetchFrame = async () => {
      try {
        const res = await fetch(`${apiUrl}/camera/frame`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.frame && imgRef.current) {
          imgRef.current.src = `data:image/jpeg;base64,${data.frame}`
        }
        if (data.fps) setFps(data.fps)
        setError('')
      } catch (err) {
        setError((err as Error).message)
      }
    }

    fetchFrame()
    const id = setInterval(fetchFrame, 1000 / refreshRate)
    return () => clearInterval(id)
  }, [isStreaming, apiUrl, refreshRate, setFps])

  const capture = () => {
    if (!imgRef.current?.src) return
    const a = document.createElement('a')
    a.href = imgRef.current.src
    a.download = `capture_${Date.now()}.jpg`
    a.click()
  }

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex-1 bg-black rounded-xl overflow-hidden flex items-center justify-center min-h-64">
        <img
          ref={imgRef}
          alt="camera feed"
          className="max-h-full max-w-full"
          style={{ display: isStreaming ? 'block' : 'none' }}
        />
        {!isStreaming && !error && (
          <p className="text-gray-400 text-sm">点击「开始」获取相机画面</p>
        )}
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </div>
      <div className="flex gap-3 shrink-0">
        <button
          onClick={() => { setIsStreaming(!isStreaming); setError('') }}
          className={`px-4 py-2 rounded-lg text-sm font-semibold text-white
            ${isStreaming ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}
        >
          {isStreaming ? '停止' : '开始'}
        </button>
        <button
          onClick={capture}
          disabled={!isStreaming}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 disabled:opacity-40"
        >
          截图
        </button>
      </div>
    </div>
  )
}

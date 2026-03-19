import { useEffect, useRef, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'
import { useStatusStore } from '../store/useStatusStore'

export const CameraPanel = () => {
  const videoRef = useRef<HTMLImageElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const { refreshRate } = useSettingsStore()
  const { setFps } = useStatusStore()

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>

    const fetchFrame = async () => {
      try {
        const response = await fetch('/api/camera/frame')
        const data = await response.json()
        if (data.frame && videoRef.current) {
          (videoRef.current as HTMLImageElement).src = `data:image/jpeg;base64,${data.frame}`
        }
        if (data.fps) {
          setFps(data.fps)
        }
      } catch (error) {
        console.error('Failed to fetch frame:', error)
      }
    }

    if (isStreaming) {
      fetchFrame()
      intervalId = setInterval(fetchFrame, 1000 / refreshRate)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [isStreaming, refreshRate, setFps])

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 bg-black rounded-lg overflow-hidden flex items-center justify-center min-h-64">
        {isStreaming
          ? <img ref={videoRef as React.RefObject<HTMLImageElement>} className="max-h-full max-w-full" alt="camera" />
          : <p className="text-gray-400">点击开始获取相机画面</p>
        }
      </div>
      <div className="mt-4 flex gap-4">
        <button
          onClick={() => setIsStreaming(!isStreaming)}
          className={`px-4 py-2 rounded ${
            isStreaming
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-green-500 hover:bg-green-600'
          } text-white`}
        >
          {isStreaming ? '停止' : '开始'}
        </button>
        <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          截图
        </button>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'

interface DetectionObject {
  id: string
  label: string
  confidence: number
  bbox: [number, number, number, number]
}

export const DetectionPanel = () => {
  const [detections, setDetections] = useState<DetectionObject[]>([])
  const [isLive, setIsLive] = useState(false)
  const { apiUrl } = useSettingsStore()

  useEffect(() => {
    if (!isLive) return
    const fetch_ = async () => {
      try {
        const res = await fetch(`${apiUrl}/detection/result`)
        const data = await res.json()
        setDetections(data.objects || [])
      } catch { /* ignore */ }
    }
    fetch_()
    const id = setInterval(fetch_, 1000)
    return () => clearInterval(id)
  }, [isLive, apiUrl])

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">目标检测结果</h2>
        <button
          onClick={() => setIsLive(!isLive)}
          className={`px-3 py-1.5 rounded-lg text-sm font-semibold text-white
            ${isLive ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}
        >
          {isLive ? '停止' : '开始检测'}
        </button>
      </div>

      <div className="flex-1 overflow-auto space-y-2">
        {detections.length === 0 ? (
          <p className="text-gray-400 text-sm text-center mt-10">
            {isLive ? '等待检测结果...' : '点击「开始检测」启动'}
          </p>
        ) : (
          detections.map((obj) => (
            <div key={obj.id} className="bg-white border border-gray-200 rounded-lg p-3 flex items-center justify-between">
              <div>
                <span className="font-semibold text-gray-800">{obj.label}</span>
                <span className="ml-2 text-xs text-gray-400">
                  bbox: [{obj.bbox.map((v) => v.toFixed(0)).join(', ')}]
                </span>
              </div>
              <span className={`text-sm font-bold ${obj.confidence > 0.7 ? 'text-green-600' : 'text-yellow-600'}`}>
                {(obj.confidence * 100).toFixed(1)}%
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

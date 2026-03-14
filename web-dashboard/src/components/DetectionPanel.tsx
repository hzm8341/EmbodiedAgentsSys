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

    const fetchDetections = async () => {
      try {
        const response = await fetch(`${apiUrl}/detection/result`)
        const data = await response.json()
        setDetections(data.objects || [])
      } catch (error) {
        console.error('Failed to fetch detections:', error)
      }
    }

    fetchDetections()
    const interval = setInterval(fetchDetections, 1000)

    return () => clearInterval(interval)
  }, [isLive, apiUrl])

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">检测结果</h2>
        <button
          onClick={() => setIsLive(!isLive)}
          className={`px-4 py-2 rounded ${
            isLive
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-green-500 hover:bg-green-600'
          } text-white`}
        >
          {isLive ? '停止' : '开始实时检测'}
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        {detections.length === 0 ? (
          <p className="text-gray-500">暂无检测结果</p>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b">
                <th className="py-2 px-4">类别</th>
                <th className="py-2 px-4">置信度</th>
                <th className="py-2 px-4">位置</th>
              </tr>
            </thead>
            <tbody>
              {detections.map((obj) => (
                <tr key={obj.id} className="border-b">
                  <td className="py-2 px-4">{obj.label}</td>
                  <td className="py-2 px-4">{(obj.confidence * 100).toFixed(1)}%</td>
                  <td className="py-2 px-4">
                    [{obj.bbox.map((v) => v.toFixed(2)).join(', ')}]
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

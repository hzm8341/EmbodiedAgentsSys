import { useStatusStore } from '../store/useStatusStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const Header = () => {
  const { connectionStatus, robotStatus } = useStatusStore()
  const { model } = useSettingsStore()

  const connColor = connectionStatus === 'connected'
    ? 'text-green-400'
    : connectionStatus === 'connecting'
    ? 'text-yellow-400'
    : 'text-red-400'

  const connLabel = connectionStatus === 'connected' ? '已连接'
    : connectionStatus === 'connecting' ? '连接中'
    : '未连接'

  const robotLabel = robotStatus === 'working' ? '执行中'
    : robotStatus === 'error' ? '异常'
    : '待机'

  return (
    <header className="h-12 bg-gray-800 text-white flex items-center px-4 justify-between shrink-0">
      <div className="flex items-center gap-5 text-sm">
        <span className="font-semibold text-white">Embodied Agents</span>
        <span className={connColor}>● {connLabel}</span>
        <span className="text-gray-300">🤖 {robotLabel}</span>
        <span className="text-gray-300">🧠 {model}</span>
      </div>
    </header>
  )
}

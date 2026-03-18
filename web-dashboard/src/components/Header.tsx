import { useStatusStore } from '../store/useStatusStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const Header = () => {
  const { connectionStatus, robotStatus, activeSkills } = useStatusStore()
  const { model } = useSettingsStore()

  return (
    <header className="h-12 bg-gray-800 text-white flex items-center px-4 justify-between">
      <div className="flex items-center gap-4">
        <span className={connectionStatus === 'connected' ? 'text-green-400' : 'text-red-400'}>
          ● {connectionStatus === 'connected' ? '已连接' : '未连接'}
        </span>
        <span>🤖 {robotStatus}</span>
        <span>🧠 {model}</span>
        <span>⚡ Skills: {activeSkills}</span>
      </div>
      <div>
        <button className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600">
          ⚙️ 设置
        </button>
      </div>
    </header>
  )
}

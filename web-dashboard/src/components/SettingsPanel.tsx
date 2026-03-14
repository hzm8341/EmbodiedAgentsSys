import { useSettingsStore, Language, Theme } from '../store/useSettingsStore'

export const SettingsPanel = () => {
  const {
    language,
    theme,
    model,
    websocketUrl,
    apiUrl,
    refreshRate,
    setLanguage,
    setTheme,
    setModel,
    setWebsocketUrl,
    setApiUrl,
    setRefreshRate,
  } = useSettingsStore()

  const models = ['Qwen3L', 'LeRobot', 'ACT', 'GR00T']

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold mb-6">设置</h2>
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">语言</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">界面风格</label>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as Theme)}
            className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
          >
            <option value="light">浅色</option>
            <option value="dark">深色</option>
            <option value="auto">自动</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">大模型选择</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
          >
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">WebSocket 地址</label>
          <input
            type="text"
            value={websocketUrl}
            onChange={(e) => setWebsocketUrl(e.target.value)}
            className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">API 地址</label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            刷新频率: {refreshRate} FPS
          </label>
          <input
            type="range"
            min="1"
            max="60"
            value={refreshRate}
            onChange={(e) => setRefreshRate(Number(e.target.value))}
            className="w-full"
          />
        </div>
      </div>
    </div>
  )
}

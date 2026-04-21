import { useSettingsStore, Language, Theme } from '../store/useSettingsStore'

const MODELS = ['Qwen3L', 'LeRobot', 'ACT', 'GR00T']

export const SettingsPanel = () => {
  const {
    language, theme, model, websocketUrl, apiUrl, refreshRate, deepseekApiKey,
    setLanguage, setTheme, setModel, setWebsocketUrl, setApiUrl, setRefreshRate, setDeepseekApiKey,
  } = useSettingsStore()

  return (
    <div className="max-w-xl space-y-6">
      <h2 className="text-xl font-semibold">设置</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">语言</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value as Language)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">界面主题</label>
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value as Theme)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          <option value="light">浅色</option>
          <option value="dark">深色</option>
          <option value="auto">自动</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">大模型</label>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        >
          {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">WebSocket 地址</label>
        <input
          type="text"
          value={websocketUrl}
          onChange={(e) => setWebsocketUrl(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">API 地址</label>
        <input
          type="text"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          相机刷新率: {refreshRate} FPS
        </label>
        <input
          type="range"
          min={1}
          max={60}
          value={refreshRate}
          onChange={(e) => setRefreshRate(Number(e.target.value))}
          className="w-full"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">DeepSeek API Key</label>
        <input
          type="password"
          value={deepseekApiKey}
          onChange={(e) => setDeepseekApiKey(e.target.value)}
          placeholder="sk-..."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>
    </div>
  )
}

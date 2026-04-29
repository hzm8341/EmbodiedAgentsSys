import { useState } from 'react'
import { useSettingsStore, Language, Theme, LLMProvider } from '../store/useSettingsStore'

export const SettingsPanel = () => {
  const {
    language,
    theme,
    model,
    websocketUrl,
    apiUrl,
    refreshRate,
    llmProvider,
    llmModel,
    llmApiKey,
    llmApiBase,
    setLanguage,
    setTheme,
    setModel,
    setWebsocketUrl,
    setApiUrl,
    setRefreshRate,
    setLLMProvider,
    setLLMModel,
    setLLMApiKey,
    setLLMApiBase,
  } = useSettingsStore()

  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{status: string; message: string} | null>(null)

  const models = ['Qwen3L', 'LeRobot', 'ACT', 'GR00T']

  // LLM 提供商选项
  const llmProviders = [
    { value: 'ollama', label: 'Ollama (本地)' },
    { value: 'deepseek', label: 'DeepSeek' },
    { value: 'openai', label: 'OpenAI' },
  ]

  // 根据提供商动态显示模型选项
  const getModelOptions = () => {
    switch (llmProvider) {
      case 'ollama':
        return ['qwen3.5:latest', 'qwen2.5:latest', 'llama3.1:latest', 'mistral:latest']
      case 'deepseek':
        return ['deepseek-chat', 'deepseek-coder']
      case 'openai':
        return ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']
      default:
        return ['qwen3.5:latest']
    }
  }

  const handleTestLLM = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const response = await fetch(`${apiUrl}/api/llm/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: llmProvider,
          model: llmModel,
          api_key: llmApiKey,
          api_base: llmApiBase,
        }),
      })
      const data = await response.json()
      setTestResult({
        status: data.status,
        message: data.status === 'ok' ? `✓ 连接成功: ${data.response}` : `✗ 错误: ${data.error}`,
      })
    } catch (e: any) {
      setTestResult({ status: 'error', message: `✗ 网络错误: ${e.message}` })
    }
    setTesting(false)
  }

  const handleSaveLLM = async () => {
    try {
      await fetch(`${apiUrl}/api/llm/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: llmProvider,
          model: llmModel,
          api_key: llmApiKey,
          api_base: llmApiBase,
        }),
      })
      setTestResult({ status: 'ok', message: '✓ 配置已保存' })
    } catch (e: any) {
      setTestResult({ status: 'error', message: `✗ 保存失败: ${e.message}` })
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold mb-6">设置</h2>
      <div className="space-y-6">
        {/* 基础设置 */}
        <div className="border-b pb-4">
          <h3 className="text-lg font-medium mb-4">基础设置</h3>

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

          <div className="mt-4">
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

          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">WebSocket 地址</label>
            <input
              type="text"
              value={websocketUrl}
              onChange={(e) => setWebsocketUrl(e.target.value)}
              className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
            />
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">API 地址</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
            />
          </div>

          <div className="mt-4">
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

        {/* LLM 配置 */}
        <div className="border-b pb-4">
          <h3 className="text-lg font-medium mb-4">大模型配置</h3>

          <div>
            <label className="block text-sm font-medium mb-2">LLM 提供商</label>
            <select
              value={llmProvider}
              onChange={(e) => setLLMProvider(e.target.value as LLMProvider)}
              className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
            >
              {llmProviders.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium mb-2">模型</label>
            <select
              value={llmModel}
              onChange={(e) => setLLMModel(e.target.value)}
              className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
            >
              {getModelOptions().map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {llmProvider !== 'ollama' && (
            <>
              <div className="mt-4">
                <label className="block text-sm font-medium mb-2">
                  API Key {llmProvider === 'deepseek' && '(sk-e5d01fe06cc64d45a022c447a31ab518)'}
                </label>
                <input
                  type="password"
                  value={llmApiKey}
                  onChange={(e) => setLLMApiKey(e.target.value)}
                  placeholder={llmProvider === 'deepseek' ? 'sk-e5d01fe06cc64d45a022c447a31ab518' : '输入 API Key'}
                  className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
                />
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium mb-2">API Base (可选)</label>
                <input
                  type="text"
                  value={llmApiBase}
                  onChange={(e) => setLLMApiBase(e.target.value)}
                  placeholder={llmProvider === 'deepseek' ? 'https://api.deepseek.com/v1' : ''}
                  className="w-full px-3 py-2 border rounded dark:bg-gray-800 dark:border-gray-700"
                />
              </div>
            </>
          )}

          <div className="mt-4 flex gap-2">
            <button
              onClick={handleTestLLM}
              disabled={testing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {testing ? '测试中...' : '测试连接'}
            </button>
            <button
              onClick={handleSaveLLM}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              保存配置
            </button>
          </div>

          {testResult && (
            <div className={`mt-3 p-3 rounded ${testResult.status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
              {testResult.message}
            </div>
          )}
        </div>

        {/* 机器人模型选择 */}
        <div>
          <h3 className="text-lg font-medium mb-4">机器人模型</h3>
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
        </div>
      </div>
    </div>
  )
}

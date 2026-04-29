import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'zh' | 'en'
export type Theme = 'light' | 'dark' | 'auto'
export type LLMProvider = 'ollama' | 'deepseek' | 'openai'

interface SettingsState {
  language: Language
  theme: Theme
  model: string
  websocketUrl: string
  apiUrl: string
  refreshRate: number
  // LLM 配置
  llmProvider: LLMProvider
  llmModel: string
  llmApiKey: string
  llmApiBase: string
  // Setters
  setLanguage: (lang: Language) => void
  setTheme: (theme: Theme) => void
  setModel: (model: string) => void
  setWebsocketUrl: (url: string) => void
  setApiUrl: (url: string) => void
  setRefreshRate: (rate: number) => void
  setLLMProvider: (provider: LLMProvider) => void
  setLLMModel: (model: string) => void
  setLLMApiKey: (key: string) => void
  setLLMApiBase: (base: string) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      language: 'zh',
      theme: 'auto',
      model: 'Qwen3L',
      websocketUrl: 'ws://localhost:8000/ws',
      apiUrl: 'http://localhost:8000/api',
      refreshRate: 30,
      // LLM 默认配置
      llmProvider: 'ollama',
      llmModel: 'qwen3.5:latest',
      llmApiKey: '',
      llmApiBase: '',
      setLanguage: (lang) => set({ language: lang }),
      setTheme: (theme) => set({ theme }),
      setModel: (model) => set({ model }),
      setWebsocketUrl: (url) => set({ websocketUrl: url }),
      setApiUrl: (url) => set({ apiUrl: url }),
      setRefreshRate: (rate) => set({ refreshRate: rate }),
      setLLMProvider: (provider) => set({ llmProvider: provider }),
      setLLMModel: (model) => set({ llmModel: model }),
      setLLMApiKey: (key) => set({ llmApiKey: key }),
      setLLMApiBase: (base) => set({ llmApiBase: base }),
    }),
    {
      name: 'dashboard-settings',
    }
  )
)

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'zh' | 'en'
export type Theme = 'light' | 'dark' | 'auto'

interface SettingsState {
  language: Language
  theme: Theme
  model: string
  websocketUrl: string
  apiUrl: string
  refreshRate: number
  deepseekApiKey: string
  setLanguage: (lang: Language) => void
  setTheme: (theme: Theme) => void
  setModel: (model: string) => void
  setWebsocketUrl: (url: string) => void
  setApiUrl: (url: string) => void
  setRefreshRate: (rate: number) => void
  setDeepseekApiKey: (key: string) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      language: 'zh',
      theme: 'auto',
      model: 'Qwen3L',
      websocketUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/agent/ws`,
      apiUrl: `${window.location.origin}/api`,
      refreshRate: 15,
      deepseekApiKey: '',
      setLanguage: (lang) => set({ language: lang }),
      setTheme: (theme) => set({ theme }),
      setModel: (model) => set({ model }),
      setWebsocketUrl: (url) => set({ websocketUrl: url }),
      setApiUrl: (url) => set({ apiUrl: url }),
      setRefreshRate: (rate) => set({ refreshRate: rate }),
      setDeepseekApiKey: (key) => set({ deepseekApiKey: key }),
    }),
    { name: 'dashboard-settings' }
  )
)

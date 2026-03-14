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
  setLanguage: (lang: Language) => void
  setTheme: (theme: Theme) => void
  setModel: (model: string) => void
  setWebsocketUrl: (url: string) => void
  setApiUrl: (url: string) => void
  setRefreshRate: (rate: number) => void
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
      setLanguage: (lang) => set({ language: lang }),
      setTheme: (theme) => set({ theme }),
      setModel: (model) => set({ model }),
      setWebsocketUrl: (url) => set({ websocketUrl: url }),
      setApiUrl: (url) => set({ apiUrl: url }),
      setRefreshRate: (rate) => set({ refreshRate: rate }),
    }),
    {
      name: 'dashboard-settings',
    }
  )
)

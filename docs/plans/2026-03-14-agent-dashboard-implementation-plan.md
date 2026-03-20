# Agent Dashboard 可视化界面实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个 Web 可视化控制面板，用于 EmbodiedAgentsSys 的实时监控与交互。

**Architecture:** 使用 FastAPI 提供后端服务（HTTP API + WebSocket），React 前端作为独立服务，前后端分离部署，支持灵活部署环境。

**Tech Stack:** React + TypeScript + Vite, Zustand, Tailwind CSS, FastAPI + Uvicorn, WebSocket

---

### Task 1: 初始化前端项目

**Files:**
- Create: `web-dashboard/package.json`
- Create: `web-dashboard/vite.config.ts`
- Create: `web-dashboard/tsconfig.json`
- Create: `web-dashboard/index.html`
- Create: `web-dashboard/src/main.tsx`

**Step 1: 创建 package.json**

```json
{
  "name": "embodied-agents-dashboard",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.24",
    "tailwindcss": "^3.3.2",
    "typescript": "^5.0.0",
    "vite": "^4.3.9"
  }
}
```

**Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

**Step 3: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**Step 4: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Embodied Agents Dashboard</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

**Step 5: 创建 src/main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
```

**Step 6: 安装依赖**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm install
```

**Step 7: 验证项目结构**

```bash
ls -la
# Expected: package.json, vite.config.ts, tsconfig.json, index.html, src/
```

**Step 8: 启动开发服务器（验证）**

```bash
pnpm dev
# Expected: Vite dev server running on http://localhost:5173
```

**Step 9: Commit**

```bash
git add web-dashboard/
git commit -m "feat: initialize web dashboard frontend project"
```

---

### Task 2: 配置 Tailwind CSS

**Files:**
- Create: `web-dashboard/tailwind.config.js`
- Create: `web-dashboard/postcss.config.js`
- Create: `web-dashboard/src/index.css`

**Step 1: 创建 tailwind.config.js**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Step 2: 创建 postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 3: 创建 src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --sidebar-width: 240px;
  --header-height: 48px;
  --footer-height: 32px;
}

html, body, #root {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
}

/* Dark mode */
.dark {
  color-scheme: dark;
}
```

**Step 4: Commit**

```bash
git add web-dashboard/tailwind.config.js web-dashboard/postcss.config.js web-dashboard/src/index.css
git commit -m "feat: configure tailwind css"
```

---

### Task 3: 创建状态管理（Zustand）

**Files:**
- Create: `web-dashboard/src/store/useSettingsStore.ts`
- Create: `web-dashboard/src/store/useStatusStore.ts`
- Create: `web-dashboard/src/store/useChatStore.ts`

**Step 1: 创建 useSettingsStore.ts**

```typescript
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
```

**Step 2: 创建 useStatusStore.ts**

```typescript
import { create } from 'zustand'

type ConnectionStatus = 'connected' | 'disconnected' | 'connecting'
type RobotStatus = 'idle' | 'working' | 'error'

interface StatusState {
  connectionStatus: ConnectionStatus
  robotStatus: RobotStatus
  activeSkills: number
  fps: number
  setConnectionStatus: (status: ConnectionStatus) => void
  setRobotStatus: (status: RobotStatus) => void
  setActiveSkills: (count: number) => void
  setFps: (fps: number) => void
}

export const useStatusStore = create<StatusState>((set) => ({
  connectionStatus: 'disconnected',
  robotStatus: 'idle',
  activeSkills: 0,
  fps: 0,
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setRobotStatus: (status) => set({ robotStatus: status }),
  setActiveSkills: (count) => set({ activeSkills: count }),
  setFps: (fps) => set({ fps }),
}))
```

**Step 3: 创建 useChatStore.ts**

```typescript
import { create } from 'zustand'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ChatState {
  messages: Message[]
  isTyping: boolean
  addMessage: (role: 'user' | 'assistant', content: string) => void
  clearMessages: () => void
  setTyping: (typing: boolean) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isTyping: false,
  addMessage: (role, content) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    }
    set({ messages: [...get().messages, message] })
  },
  clearMessages: () => set({ messages: [] }),
  setTyping: (typing) => set({ isTyping: typing }),
}))
```

**Step 4: Commit**

```bash
git add web-dashboard/src/store/
git commit -m "feat: create zustand state management stores"
```

---

### Task 4: 创建组件骨架

**Files:**
- Create: `web-dashboard/src/components/Header.tsx`
- Create: `web-dashboard/src/components/Sidebar.tsx`
- Create: `web-dashboard/src/components/MainArea.tsx`
- Create: `web-dashboard/src/components/StatusBadge.tsx`
- Modify: `web-dashboard/src/App.tsx`

**Step 1: 创建 Header.tsx**

```typescript
import React from 'react'
import { useStatusStore } from '../store/useStatusStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const Header: React.FC = () => {
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
```

**Step 2: 创建 Sidebar.tsx**

```typescript
import React from 'react'

type SidebarItem = {
  id: string
  icon: string
  label: string
}

const items: SidebarItem[] = [
  { id: 'chat', icon: '📝', label: '对话' },
  { id: 'camera', icon: '📷', label: '相机' },
  { id: 'detection', icon: '🎯', label: '检测' },
  { id: 'settings', icon: '⚙️', label: '设置' },
]

interface SidebarProps {
  activeItem: string
  onItemSelected: (id: string) => void
}

export const Sidebar: React.FC<SidebarProps> = ({ activeItem, onItemSelected }) => {
  return (
    <aside className="w-60 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Embodied Agents</h2>
      </div>
      <nav className="flex-1 py-4">
        {items.map((item) => (
          <button
            key={item.id}
            onClick={() => onItemSelected(item.id)}
            className={`w-full px-4 py-3 text-left flex items-center gap-3 hover:bg-gray-800 ${
              activeItem === item.id ? 'bg-gray-700' : ''
            }`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}
```

**Step 3: 创建 MainArea.tsx**

```typescript
import React from 'react'

interface MainAreaProps {
  activeItem: string
}

export const MainArea: React.FC<MainAreaProps> = ({ activeItem }) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">对话面板</h2>
          <p>对话内容将在这里显示...</p>
        </div>
      )}
      {activeItem === 'camera' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">相机画面</h2>
          <p>相机画面将在这里显示...</p>
        </div>
      )}
      {activeItem === 'detection' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">检测结果</h2>
          <p>检测结果将在这里显示...</p>
        </div>
      )}
      {activeItem === 'settings' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">设置</h2>
          <p>设置面板将在这里显示...</p>
        </div>
      )}
    </main>
  )
}
```

**Step 4: 修改 App.tsx**

```typescript
import React, { useState } from 'react'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { MainArea } from './components/MainArea'

function App() {
  const [activeItem, setActiveItem] = useState('chat')

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeItem={activeItem} onItemSelected={setActiveItem} />
        <MainArea activeItem={activeItem} />
      </div>
    </div>
  )
}

export default App
```

**Step 5: Commit**

```bash
git add web-dashboard/src/components/ web-dashboard/src/App.tsx
git commit -m "feat: create layout components (Header, Sidebar, MainArea)"
```

---

### Task 5: 创建聊天对话面板

**Files:**
- Create: `web-dashboard/src/components/ChatPanel.tsx`
- Modify: `web-dashboard/src/components/MainArea.tsx`

**Step 1: 创建 ChatPanel.tsx**

```typescript
import React, { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../store/useChatStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const ChatPanel: React.FC = () => {
  const { messages, isTyping, addMessage, setTyping } = useChatStore()
  const { apiUrl } = useSettingsStore()
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!inputValue.trim()) return

    addMessage('user', inputValue)
    setInputValue('')
    setTyping(true)

    try {
      const response = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputValue }),
      })
      const data = await response.json()
      addMessage('assistant', data.response)
    } catch (error) {
      addMessage('assistant', '抱歉，发送消息失败。')
    } finally {
      setTyping(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-md px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 dark:bg-gray-700'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="text-gray-500 text-sm">正在输入...</div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入消息..."
            className="flex-1 px-4 py-2 border rounded-lg dark:bg-gray-800 dark:border-gray-700"
          />
          <button
            onClick={handleSend}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  )
}
```

**Step 2: 修改 MainArea.tsx**

```typescript
import React from 'react'
import { ChatPanel } from './ChatPanel'

interface MainAreaProps {
  activeItem: string
}

export const MainArea: React.FC<MainAreaProps> = ({ activeItem }) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && <ChatPanel />}
      {activeItem === 'camera' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">相机画面</h2>
          <p>相机画面将在这里显示...</p>
        </div>
      )}
      {activeItem === 'detection' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">检测结果</h2>
          <p>检测结果将在这里显示...</p>
        </div>
      )}
      {activeItem === 'settings' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">设置</h2>
          <p>设置面板将在这里显示...</p>
        </div>
      )}
    </main>
  )
}
```

**Step 3: Commit**

```bash
git add web-dashboard/src/components/ChatPanel.tsx web-dashboard/src/components/MainArea.tsx
git commit -m "feat: create chat panel component"
```

---

### Task 6: 创建相机画面面板

**Files:**
- Create: `web-dashboard/src/components/CameraPanel.tsx`
- Modify: `web-dashboard/src/components/MainArea.tsx`

**Step 1: 创建 CameraPanel.tsx**

```typescript
import React, { useEffect, useRef, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'
import { useStatusStore } from '../store/useStatusStore'

export const CameraPanel: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const { refreshRate } = useSettingsStore()
  const { setFps } = useStatusStore()

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const fetchFrame = async () => {
      try {
        const response = await fetch('/api/camera/frame')
        const data = await response.json()
        if (data.frame && videoRef.current) {
          videoRef.current.src = `data:image/jpeg;base64,${data.frame}`
        }
        if (data.fps) {
          setFps(data.fps)
        }
      } catch (error) {
        console.error('Failed to fetch frame:', error)
      }
    }

    if (isStreaming) {
      fetchFrame()
      intervalId = setInterval(fetchFrame, 1000 / refreshRate)
    }

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [isStreaming, refreshRate, setFps])

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 bg-black rounded-lg overflow-hidden flex items-center justify-center">
        <video
          ref={videoRef}
          className="max-h-full max-w-full"
          autoPlay
          playsInline
        />
        {!isStreaming && (
          <p className="text-gray-400">点击开始获取相机画面</p>
        )}
      </div>
      <div className="mt-4 flex gap-4">
        <button
          onClick={() => setIsStreaming(!isStreaming)}
          className={`px-4 py-2 rounded ${
            isStreaming
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-green-500 hover:bg-green-600'
          } text-white`}
        >
          {isStreaming ? '停止' : '开始'}
        </button>
        <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          截图
        </button>
      </div>
    </div>
  )
}
```

**Step 2: 修改 MainArea.tsx**

```typescript
import React from 'react'
import { ChatPanel } from './ChatPanel'
import { CameraPanel } from './CameraPanel'

interface MainAreaProps {
  activeItem: string
}

export const MainArea: React.FC<MainAreaProps> = ({ activeItem }) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && <ChatPanel />}
      {activeItem === 'camera' && <CameraPanel />}
      {activeItem === 'detection' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">检测结果</h2>
          <p>检测结果将在这里显示...</p>
        </div>
      )}
      {activeItem === 'settings' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">设置</h2>
          <p>设置面板将在这里显示...</p>
        </div>
      )}
    </main>
  )
}
```

**Step 3: Commit**

```bash
git add web-dashboard/src/components/CameraPanel.tsx web-dashboard/src/components/MainArea.tsx
git commit -m "feat: create camera panel component"
```

---

### Task 7: 创建检测结果面板

**Files:**
- Create: `web-dashboard/src/components/DetectionPanel.tsx`
- Modify: `web-dashboard/src/components/MainArea.tsx`

**Step 1: 创建 DetectionPanel.tsx**

```typescript
import React, { useEffect, useState } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'

interface DetectionObject {
  id: string
  label: string
  confidence: number
  bbox: [number, number, number, number]
}

export const DetectionPanel: React.FC = () => {
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
```

**Step 2: 修改 MainArea.tsx**

```typescript
import React from 'react'
import { ChatPanel } from './ChatPanel'
import { CameraPanel } from './CameraPanel'
import { DetectionPanel } from './DetectionPanel'

interface MainAreaProps {
  activeItem: string
}

export const MainArea: React.FC<MainAreaProps> = ({ activeItem }) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && <ChatPanel />}
      {activeItem === 'camera' && <CameraPanel />}
      {activeItem === 'detection' && <DetectionPanel />}
      {activeItem === 'settings' && (
        <div>
          <h2 className="text-xl font-semibold mb-4">设置</h2>
          <p>设置面板将在这里显示...</p>
        </div>
      )}
    </main>
  )
}
```

**Step 3: Commit**

```bash
git add web-dashboard/src/components/DetectionPanel.tsx web-dashboard/src/components/MainArea.tsx
git commit -m "feat: create detection panel component"
```

---

### Task 8: 创建设置面板

**Files:**
- Create: `web-dashboard/src/components/SettingsPanel.tsx`
- Modify: `web-dashboard/src/components/MainArea.tsx`

**Step 1: 创建 SettingsPanel.tsx**

```typescript
import React from 'react'
import { useSettingsStore, Language, Theme } from '../store/useSettingsStore'

export const SettingsPanel: React.FC = () => {
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
```

**Step 2: 修改 MainArea.tsx**

```typescript
import React from 'react'
import { ChatPanel } from './ChatPanel'
import { CameraPanel } from './CameraPanel'
import { DetectionPanel } from './DetectionPanel'
import { SettingsPanel } from './SettingsPanel'

interface MainAreaProps {
  activeItem: string
}

export const MainArea: React.FC<MainAreaProps> = ({ activeItem }) => {
  return (
    <main className="flex-1 bg-gray-100 dark:bg-gray-900 p-6 overflow-auto">
      {activeItem === 'chat' && <ChatPanel />}
      {activeItem === 'camera' && <CameraPanel />}
      {activeItem === 'detection' && <DetectionPanel />}
      {activeItem === 'settings' && <SettingsPanel />}
    </main>
  )
}
```

**Step 3: Commit**

```bash
git add web-dashboard/src/components/SettingsPanel.tsx web-dashboard/src/components/MainArea.tsx
git commit -m "feat: create settings panel component"
```

---

### Task 9: 创建后端服务

**Files:**
- Create: `examples/agent_dashboard_backend.py`

**Step 1: 创建 FastAPI 后端**

```python
"""
Agent Dashboard Backend Service
"""
import asyncio
import base64
import json
from typing import Optional
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import numpy as np

app = FastAPI(title="Embodied Agents Dashboard Backend")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: datetime


class Settings(BaseModel):
    language: str
    theme: str
    model: str
    websocket_url: str
    api_url: str
    refresh_rate: int


# 模拟数据
MOCK_CAMERA_FRAME = base64.b64encode(b"mock_image_data").decode()
MOCK_DETECTIONS = [
    {"id": "1", "label": "cube", "confidence": 0.95, "bbox": [0.1, 0.2, 0.3, 0.4]},
    {"id": "2", "label": "cup", "confidence": 0.87, "bbox": [0.5, 0.3, 0.2, 0.3]},
]


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天消息"""
    # 这里可以集成实际的 VLA/LLM
    response_text = f"收到消息: {request.message}"
    return ChatResponse(response=response_text, timestamp=datetime.now())


@app.get("/api/camera/frame")
async def get_camera_frame():
    """获取相机画面帧"""
    return {
        "frame": MOCK_CAMERA_FRAME,
        "timestamp": datetime.now(),
        "fps": 30,
    }


@app.get("/api/detection/result")
async def get_detection_result():
    """获取检测结果"""
    return {
        "objects": MOCK_DETECTIONS,
        "timestamp": datetime.now(),
    }


@app.get("/api/settings", response_model=Settings)
async def get_settings():
    """获取设置"""
    return Settings(
        language="zh",
        theme="auto",
        model="Qwen3L",
        websocket_url="ws://localhost:8000/ws",
        api_url="http://localhost:8000/api",
        refresh_rate=30,
    )


@app.put("/api/settings")
async def update_settings(settings: Settings):
    """更新设置"""
    return {"status": "updated"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时数据推送"""
    await websocket.accept()
    try:
        while True:
            # 模拟推送相机帧
            await asyncio.sleep(0.1)
            data = {
                "type": "camera_frame",
                "frame": MOCK_CAMERA_FRAME,
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_json(data)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: 测试后端服务**

```bash
# 运行后端
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. python examples/agent_dashboard_backend.py

# 或使用 uvicorn
PYTHONPATH=. uvicorn examples.agent_dashboard_backend:app --reload --port 8000

# 测试健康检查
curl http://localhost:8000/healthz
# Expected: {"status":"ok"}

# 测试聊天接口
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
# Expected: {"response":"收到消息: hello", "timestamp":...}
```

**Step 3: Commit**

```bash
git add examples/agent_dashboard_backend.py
git commit -m "feat: create FastAPI backend for dashboard"
```

---

### Task 10: 测试与验证

**Step 1: 启动后端服务**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. uvicorn examples.agent_dashboard_backend:app --reload --port 8000
```

**Step 2: 启动前端服务**

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm dev
```

**Step 3: 验证各模块**

1. **打开浏览器访问** `http://localhost:5173`
2. **检查顶部状态栏**：显示连接状态、机器人状态、模型、Skills 数量
3. **测试侧边栏导航**：点击各菜单项，主区域切换正确
4. **测试聊天面板**：输入消息并发送，显示历史记录
5. **测试相机面板**：点击开始，显示模拟画面
6. **测试检测面板**：点击开始实时检测，显示检测结果
7. **测试设置面板**：修改设置，保存成功

**Step 4: 创建测试脚本**

Create: `web-dashboard/test.sh`

```bash
#!/bin/bash
echo "Starting Dashboard Tests..."

# Check backend
echo "Checking backend..."
curl -s http://localhost:8000/healthz | grep -q "ok" && echo "✓ Backend OK" || echo "✗ Backend FAIL"

# Check frontend
echo "Checking frontend..."
curl -s http://localhost:5173 | grep -q "root" && echo "✓ Frontend OK" || echo "✗ Frontend FAIL"

echo "Done."
```

**Step 5: Commit**

```bash
git add web-dashboard/test.sh
git commit -m "feat: add test script"
```

---

### Task 11: 创建部署文档

**Files:**
- Create: `docs/guides/dashboard-deployment.md`

**Step 1: 创建部署文档**

```markdown
# Agent Dashboard 部署指南

## 开发环境部署

### 1. 启动后端服务

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. uvicorn examples.agent_dashboard_backend:app --reload --port 8000
```

### 2. 启动前端服务

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm dev
```

### 3. 访问界面

打开浏览器访问 `http://localhost:5173`

## 生产环境部署

### 前端构建

```bash
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm build
```

### 部署方式

1. 使用 Nginx 托管静态文件
2. 后端服务使用 Docker 容器化部署
```

**Step 2: Commit**

```bash
git add docs/guides/dashboard-deployment.md
git commit -m "docs: add dashboard deployment guide"
```

---

### Task 12: 完整验证

**Step 1: 运行完整测试**

```bash
# 启动后端
cd /media/hzm/data_disk/EmbodiedAgentsSys
PYTHONPATH=. uvicorn examples.agent_dashboard_backend:app --reload --port 8000 &

# 启动前端
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm dev &

# 访问 http://localhost:5173 并手动验证
```

**Step 2: 检查所有功能**

- [ ] 顶部状态栏显示正确
- [ ] 侧边栏导航正常
- [ ] 聊天面板发送消息并显示
- [ ] 相机画面显示正常
- [ ] 检测结果面板正常
- [ ] 设置面板保存正常
- [ ] WebSocket 连接正常

**Step 3: Final Commit**

```bash
git add .
git commit -m "feat: complete agent dashboard implementation"
```

---

## 执行选项

Plan complete and saved to `docs/plans/2026-03-14-agent-dashboard-implementation-plan.md`.

**Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach would you like to use?
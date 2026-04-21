import { create } from 'zustand'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: { tool: string; params: Record<string, unknown>; result: Record<string, unknown> }[]
  timestamp: Date
}

interface ChatState {
  messages: Message[]
  isTyping: boolean
  addMessage: (role: 'user' | 'assistant', content: string, toolCalls?: Message['toolCalls']) => void
  clearMessages: () => void
  setTyping: (typing: boolean) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isTyping: false,
  addMessage: (role, content, toolCalls) => {
    const message: Message = {
      id: Date.now().toString(),
      role,
      content,
      toolCalls,
      timestamp: new Date(),
    }
    set({ messages: [...get().messages, message] })
  },
  clearMessages: () => set({ messages: [] }),
  setTyping: (typing) => set({ isTyping: typing }),
}))

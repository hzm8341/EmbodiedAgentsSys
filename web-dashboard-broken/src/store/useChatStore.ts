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

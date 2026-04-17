import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '../store/useChatStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const ChatPanel = () => {
  const { messages, isTyping, addMessage, setTyping } = useChatStore()
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

    const { apiKey } = useSettingsStore.getState()
    if (!apiKey) {
      addMessage('assistant', '请先在设置中配置 DeepSeek API Key')
      return
    }

    addMessage('user', inputValue)
    setInputValue('')
    setTyping(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ message: inputValue }),
      })
      const data = await response.json()
      addMessage('assistant', data.response)
    } catch {
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

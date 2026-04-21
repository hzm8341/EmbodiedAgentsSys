import { useRef, useState } from 'react'
import { useChatStore } from '../store/useChatStore'
import { useSettingsStore } from '../store/useSettingsStore'

export const ChatPanel = () => {
  const { messages, isTyping, addMessage, clearMessages, setTyping } = useChatStore()
  const { apiUrl, deepseekApiKey } = useSettingsStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const send = async () => {
    if (!input.trim() || isTyping) return
    const text = input
    addMessage('user', text)
    setInput('')
    setTyping(true)

    const history = messages.map((m) => ({ role: m.role, content: m.content }))

    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(deepseekApiKey ? { 'x-api-key': deepseekApiKey } : {}),
        },
        body: JSON.stringify({ message: text, history }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || '请求失败')
      }
      const data = await res.json()
      addMessage(
        'assistant',
        data.response || `已执行 ${data.tool_calls?.length ?? 0} 个工具调用`,
        data.tool_calls,
      )
    } catch (err) {
      addMessage('assistant', `错误: ${(err as Error).message}`)
    } finally {
      setTyping(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    }
  }

  return (
    <div className="flex flex-col h-full gap-3">
      {/* 无 API Key 时的提示 */}
      {!deepseekApiKey && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 flex items-center gap-2 shrink-0 text-sm text-amber-700">
          <span>⚠</span>
          <span>未配置 DeepSeek API Key，请前往 <strong>⚙️ 设置</strong> 页面填写后再使用。</span>
        </div>
      )}

      {/* 消息列表 */}
      <div className="flex-1 bg-white rounded-lg border border-gray-200 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
          <span className="text-xs font-semibold text-gray-500">对话记录</span>
          <button onClick={clearMessages} className="text-xs text-gray-400 hover:text-red-500">清空</button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 text-sm mt-10">
            用自然语言控制机器人，例如：「将左臂移动到 x=0.3 y=0 z=0.5」
          </p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[72%] px-4 py-2 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-sm'
                  : 'bg-gray-100 text-gray-800 rounded-bl-sm'}`}
            >
              <p className="m-0">{msg.content}</p>
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.toolCalls.map((tc, i) => (
                    <div key={i} className="bg-gray-200 rounded p-2 text-xs">
                      <span className="font-bold text-blue-600">⚙ {tc.tool}</span>
                      <pre className="mt-1 text-gray-600 whitespace-pre-wrap break-all font-mono">
                        {JSON.stringify(tc.params, null, 2)}
                        {'\n→ '}
                        {JSON.stringify(tc.result, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1 items-center">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
        </div>
      </div>

      {/* 输入栏 */}
      <div className="flex gap-2 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="输入指令，按 Enter 发送..."
          disabled={isTyping}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
        />
        <button
          onClick={send}
          disabled={isTyping || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          发送
        </button>
      </div>
    </div>
  )
}

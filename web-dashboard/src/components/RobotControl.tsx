import { useState, useEffect } from 'react'
import { DeepSeekService, executeAction, getScene, resetEnv, type DeepSeekMessage, type ToolCall } from '../services/deepseek'

const API_KEY = import.meta.env.VITE_DEEPSEEK_API_KEY || "sk-985a3370aeb04666969329b5af10d9f9"

interface Message {
  role: string
  content: string
}

export const RobotControl = () => {
  const [userInput, setUserInput] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [scene, setScene] = useState({ robot_position: [0, 0, 0], object_position: [0, 0, 0] })
  const deepseek = new DeepSeekService(API_KEY)

  useEffect(() => { refreshScene() }, [])

  const refreshScene = async () => {
    try {
      const data = await getScene()
      setScene(data)
    } catch (e) { console.error("Failed to get scene:", e) }
  }

  const executeToolCall = async (toolCall: ToolCall) => {
    const { name, arguments: argsStr } = toolCall.function
    const params = JSON.parse(argsStr)
    return executeAction(name, params)
  }

  const handleSubmit = async () => {
    const msg = userInput.trim()
    if (!msg) return
    setMessages(prev => [...prev, { role: "user", content: msg }])
    setUserInput("")
    setIsLoading(true)
    try {
      const systemPrompt: DeepSeekMessage = {
        role: "system",
        content: "你是一个机器人控制助手。用户用自然语言描述命令，你需要调用适当的工具来控制机器人。机器人支持: move_to(x,y,z), move_relative(dx,dy,dz), grasp, release, get_scene。"
      }
      const allMessages: DeepSeekMessage[] = [
        systemPrompt,
        ...messages.map(m => ({ role: m.role as "user" | "assistant", content: m.content })),
        { role: "user" as const, content: msg }
      ]
      const response = await deepseek.chat(allMessages)
      const assistantMsg = response.message
      setMessages(prev => [...prev, { role: "assistant", content: assistantMsg.content || "" }])
      if (assistantMsg.tool_calls) {
        for (const toolCall of assistantMsg.tool_calls) {
          const result = await executeToolCall(toolCall)
          setMessages(prev => [...prev, { role: "assistant", content: `[${toolCall.function.name}] 结果: ${JSON.stringify(result)}` }])
        }
        await refreshScene()
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: `错误: ${e}` }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = async () => {
    await resetEnv()
    await refreshScene()
    setMessages([])
  }

  return (
    <div className="robot-control p-4">
      <h2 className="text-xl font-bold mb-4">🤖 机器人控制</h2>
      <div className="scene-status mb-4 p-3 bg-gray-100 rounded dark:bg-gray-800">
        <div>机器人位置: {scene.robot_position?.join(', ') || 'N/A'}</div>
        <div>物体位置: {scene.object_position?.join(', ') || 'N/A'}</div>
      </div>
      <div className="messages h-64 overflow-y-auto border rounded p-3 mb-4 dark:bg-gray-800">
        {messages.map((msg, i) => <div key={i} className="mb-2"><strong>{msg.role === 'user' ? '👤' : '🤖'}</strong>: {msg.content}</div>)}
        {isLoading && <div className="text-gray-500">思考中...</div>}
      </div>
      <div className="flex gap-2">
        <input value={userInput} onChange={e => setUserInput(e.target.value)} onKeyUp={e => e.key === 'Enter' && handleSubmit()}
          placeholder="输入命令，如: 将机器人移动到 x=0.5 y=0 z=0.3" className="flex-1 border rounded px-3 py-2 dark:bg-gray-800 dark:text-white" disabled={isLoading} />
        <button onClick={handleSubmit} disabled={isLoading} className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50">发送</button>
        <button onClick={handleReset} className="bg-gray-300 px-4 py-2 rounded dark:bg-gray-700">重置</button>
      </div>
      <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
        <p>可用命令示例:</p>
        <ul className="list-disc list-inside">
          <li>将机器人移动到 x=0.5 y=0 z=0.3</li><li>向上移动 0.1 米</li><li>抓取物体</li><li>释放物体</li>
        </ul>
      </div>
    </div>
  )
}

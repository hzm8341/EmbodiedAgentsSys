<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { DeepSeekService, executeAction, getScene, resetEnv, ROBOT_TOOLS, type DeepSeekMessage, type ToolCall } from '../services/deepseek'

const API_KEY = import.meta.env.VITE_DEEPSEEK_API_KEY || "sk-985a3370aeb04666969329b5af10d9f9"

const userInput = ref("")
const messages = ref<Array<{role: string, content: string}>>([])
const isLoading = ref(false)
const scene = ref({ robot_position: [0, 0, 0], object_position: [0, 0, 0] })
const deepseek = new DeepSeekService(API_KEY)

onMounted(async () => {
  await refreshScene()
})

async function refreshScene() {
  try {
    scene.value = await getScene()
  } catch (e) {
    console.error("Failed to get scene:", e)
  }
}

async function handleSubmit() {
  const userMsg = userInput.value.trim()
  if (!userMsg) return

  // 添加用户消息
  messages.value.push({ role: "user", content: userMsg })
  userInput.value = ""
  isLoading.value = true

  try {
    // 调用 DeepSeek
    const systemPrompt: DeepSeekMessage = {
      role: "system",
      content: "你是一个机器人控制助手。用户用自然语言描述命令，你需要调用适当的工具来控制机器人。机器人支持: move_to(x,y,z), move_relative(dx,dy,dz), grasp, release, get_scene。"
    }

    const allMessages: DeepSeekMessage[] = [
      systemPrompt,
      ...messages.value.map(m => ({ role: m.role as "user" | "assistant", content: m.content }))
    ]

    const response = await deepseek.chat(allMessages)
    const assistantMsg = response.message

    // 添加助手消息
    messages.value.push({ role: "assistant", content: assistantMsg.content || "" })

    // 处理工具调用
    if (assistantMsg.tool_calls) {
      for (const toolCall of assistantMsg.tool_calls) {
        const result = await executeToolCall(toolCall)
        messages.value.push({
          role: "assistant",
          content: `[${toolCall.function.name}] 结果: ${JSON.stringify(result)}`
        })
      }
      await refreshScene()
    }
  } catch (e) {
    messages.value.push({ role: "assistant", content: `错误: ${e}` })
  } finally {
    isLoading.value = false
  }
}

async function executeToolCall(toolCall: ToolCall) {
  const { name, arguments: argsStr } = toolCall.function
  const params = JSON.parse(argsStr)
  return executeAction(name, params)
}

async function handleReset() {
  await resetEnv()
  await refreshScene()
  messages.value = []
}
</script>

<template>
  <div class="robot-control p-4">
    <h2 class="text-xl font-bold mb-4">🤖 机器人控制</h2>

    <!-- 场景状态 -->
    <div class="scene-status mb-4 p-3 bg-gray-100 rounded">
      <div>机器人位置: {{ scene.robot_position?.join(', ') || 'N/A' }}</div>
      <div>物体位置: {{ scene.object_position?.join(', ') || 'N/A' }}</div>
    </div>

    <!-- 消息列表 -->
    <div class="messages h-64 overflow-y-auto border rounded p-3 mb-4">
      <div v-for="(msg, i) in messages" :key="i" class="mb-2">
        <strong>{{ msg.role === 'user' ? '👤' : '🤖' }}:</strong> {{ msg.content }}
      </div>
      <div v-if="isLoading" class="text-gray-500">思考中...</div>
    </div>

    <!-- 输入框 -->
    <div class="flex gap-2">
      <input
        v-model="userInput"
        @keyup.enter="handleSubmit"
        placeholder="输入命令，如: 将机器人移动到 x=0.5 y=0 z=0.3"
        class="flex-1 border rounded px-3 py-2"
        :disabled="isLoading"
      />
      <button
        @click="handleSubmit"
        :disabled="isLoading"
        class="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
      >
        发送
      </button>
      <button
        @click="handleReset"
        class="bg-gray-300 px-4 py-2 rounded"
      >
        重置
      </button>
    </div>

    <!-- 可用工具说明 -->
    <div class="mt-4 text-sm text-gray-600">
      <p>可用命令示例:</p>
      <ul class="list-disc list-inside">
        <li>将机器人移动到 x=0.5 y=0 z=0.3</li>
        <li>向上移动 0.1 米</li>
        <li>抓取物体</li>
        <li>释放物体</li>
      </ul>
    </div>
  </div>
</template>

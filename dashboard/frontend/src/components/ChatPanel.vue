<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { chatApi, type ChatMessage } from '@/api/client'

const props = defineProps<{ decisionId: number }>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)

onMounted(async () => {
  try {
    const res = await chatApi.getHistory(props.decisionId)
    messages.value = res.data
  } catch {}
})

async function send() {
  if (!inputText.value.trim()) return
  const userMsg: ChatMessage = { role: 'human', content: inputText.value }
  messages.value.push(userMsg)
  const savedMsg = inputText.value
  inputText.value = ''
  loading.value = true
  try {
    await chatApi.send(props.decisionId, savedMsg)
    messages.value.push({ role: 'agent', content: '收到您的问题，正在分析中...（流式响应 Phase 2 实现）' })
  } catch {
    messages.value.push({ role: 'agent', content: '发送失败，请重试。' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="chat-panel">
    <div class="chat-messages">
      <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
        <div class="bubble">{{ msg.content }}</div>
      </div>
      <div v-if="loading" class="message agent">
        <div class="bubble">思考中...</div>
      </div>
    </div>
    <div class="chat-input">
      <el-input v-model="inputText" placeholder="追问详情..." @keyup.enter="send" :disabled="loading" />
      <el-button type="primary" @click="send" :loading="loading">发送</el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  margin-top: 12px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}
.chat-messages {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}
.message { display: flex; }
.message.human { justify-content: flex-end; }
.bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.message.human .bubble { background: var(--accent); color: white; }
.message.agent .bubble { background: var(--bg-secondary); color: var(--text-secondary); }
.chat-input { display: flex; gap: 8px; }
</style>

<template>
  <el-card shadow="hover" class="chat-card" body-style="padding: 0; display: flex; flex-direction: column; height: 100%;">
    <template #header>
      <div class="card-header">
        <span>智能对话</span>
        <el-button size="small" text @click="showHistory = !showHistory">
          <el-icon><Clock /></el-icon> 历史
        </el-button>
      </div>
    </template>

    <!-- History sidebar -->
    <div v-if="showHistory" class="history-panel">
      <div class="history-header">
        <span>历史会话</span>
        <el-button size="small" text @click="showHistory = false"><el-icon><Close /></el-icon></el-button>
      </div>
      <div class="history-list" v-loading="historyLoading">
        <div v-if="sessions.length === 0" class="history-empty">暂无历史记录</div>
        <div
          v-for="s in sessions" :key="s.id"
          class="history-item"
          :class="{ active: s.id === currentSessionId }"
          @click="loadSession(s)"
        >
          <div class="history-filename">{{ s.filename || '未命名' }}</div>
          <div class="history-meta">{{ s.rows }}行 · {{ s.created_at?.slice(0, 16) }}</div>
          <el-button class="history-del" size="small" text type="danger" @click.stop="handleDelete(s.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div class="messages" ref="messagesRef" v-show="!showHistory">
      <div v-if="store.messages.length === 0" class="empty-hint">
        <p>上传数据后，输入自然语言指令开始分析</p>
        <p class="examples">例如："分析销售趋势并生成图表"</p>
      </div>
      <div v-for="(msg, i) in store.messages" :key="i" :class="['msg', msg.role]">
        <div class="msg-content" v-html="formatMessage(msg.content)"></div>
      </div>
      <div v-if="streaming" class="msg assistant">
        <div class="msg-content">{{ streamText }}<span class="cursor">|</span></div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-area" v-show="!showHistory">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        placeholder="输入分析指令，如：分析各产品销售额占比..."
        @keydown.enter.ctrl="send"
        :disabled="streaming"
      />
      <el-button type="primary" @click="send" :loading="streaming" :disabled="!input.trim()">
        发送 (Ctrl+Enter)
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { Clock, Close, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '../stores/app'
import { chatStream, getSessions, getSessionDetail, deleteSession as apiDeleteSession } from '../api'

const store = useAppStore()
const input = ref('')
const streaming = ref(false)
const streamText = ref('')
const messagesRef = ref(null)
const showHistory = ref(false)
const historyLoading = ref(false)
const sessions = ref([])
const currentSessionId = ref('default')

function formatMessage(text) {
  return text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

async function send() {
  const msg = input.value.trim()
  if (!msg) return
  input.value = ''
  store.addMessage({ role: 'user', content: msg })
  scrollToBottom()

  streaming.value = true
  streamText.value = ''

  try {
    const response = await chatStream(msg)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()

      let eventType = null
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim()
        } else if (line.startsWith('data:') && eventType) {
          try {
            const data = JSON.parse(line.slice(5))
            if (eventType === 'text' && typeof data === 'string') {
              streamText.value += data
              scrollToBottom()
            } else if (eventType === 'charts') {
              store.updateCharts(data)
            } else if (eventType === 'analysis') {
              store.analysisResult = { ...store.analysisResult, ...data }
            } else if (eventType === 'status') {
              streamText.value += `\n[${data}]\n`
            }
          } catch (_) {}
          eventType = null
        }
      }
    }

    if (streamText.value) {
      store.addMessage({ role: 'assistant', content: streamText.value })
    }
  } catch (e) {
    store.addMessage({ role: 'assistant', content: '抱歉，发生了错误。请检查后端服务是否启动。' })
  } finally {
    streaming.value = false
    streamText.value = ''
    scrollToBottom()
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const { data } = await getSessions()
    sessions.value = data.sessions || []
  } catch (_) {} finally {
    historyLoading.value = false
  }
}

async function loadSession(s) {
  try {
    const { data } = await getSessionDetail(s.id)
    currentSessionId.value = s.id
    store.messages = (data.messages || []).map(m => ({ role: m.role, content: m.content }))
    if (data.analyses?.length) {
      const last = data.analyses[data.analyses.length - 1]
      store.analysisResult = last.metrics || {}
    }
    showHistory.value = false
    ElMessage.success(`已加载会话: ${s.filename}`)
  } catch (_) {
    ElMessage.error('加载会话失败')
  }
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定删除该历史记录？', '确认')
    await apiDeleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    ElMessage.success('已删除')
  } catch (_) {}
}

onMounted(loadHistory)
</script>

<style scoped>
.chat-card { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }

.history-panel { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.history-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px; font-weight: 600;
}
.history-list { flex: 1; overflow-y: auto; padding: 8px; }
.history-empty { text-align: center; color: #999; padding: 30px 0; font-size: 13px; }
.history-item {
  padding: 10px 12px; border-radius: 6px; cursor: pointer; position: relative;
  margin-bottom: 4px; border: 1px solid #eee; transition: all 0.15s;
}
.history-item:hover { background: #f5f7fa; border-color: #d9ecff; }
.history-item.active { background: #ecf5ff; border-color: #409eff; }
.history-filename { font-size: 13px; font-weight: 500; color: #303133; }
.history-meta { font-size: 11px; color: #909399; margin-top: 4px; }
.history-del { position: absolute; top: 8px; right: 8px; opacity: 0; transition: opacity 0.15s; }
.history-item:hover .history-del { opacity: 1; }

.messages {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.empty-hint { text-align: center; color: #999; padding: 40px 0; }
.empty-hint .examples { font-size: 12px; color: #bbb; margin-top: 8px; }
.msg { max-width: 90%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.msg.user { align-self: flex-end; background: #409eff; color: #fff; border-bottom-right-radius: 4px; }
.msg.assistant { align-self: flex-start; background: #f4f4f5; color: #333; border-bottom-left-radius: 4px; }
.msg-content { word-break: break-word; }
.cursor { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0; } }
.input-area { padding: 12px; border-top: 1px solid #eee; display: flex; gap: 8px; }
.input-area .el-input { flex: 1; }
</style>

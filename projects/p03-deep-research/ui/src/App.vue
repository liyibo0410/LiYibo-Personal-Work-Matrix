<script setup lang="ts">
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import axios from 'axios'
import { marked } from 'marked'

// Types
interface Message {
  role: 'user' | 'ai' | 'system'
  content: string
  logs?: LogItem[]
  files?: FileItem[]
  timestamp?: number
}

interface LogItem {
  type: string
  title: string
  details: any
  timestamp: string
}

interface FileItem {
  name: string
  path: string
  url: string
}

// 公网演示走 http（非安全上下文），crypto.randomUUID 在部分浏览器不可用；
// genId() 统一降级到手工实现，避免「crypto.randomUUID is not a function」。
function genId(): string {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID()
  } catch (e) {}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c: string): string => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// State
const inputQuery = ref('')
const messages = ref<Message[]>([])
const status = ref<'idle' | 'running'>('idle')
const socket = ref<WebSocket | null>(null)
const currentSessionPath = ref('')
const currentSessionUrl = ref('')
const messagesEndRef = ref<HTMLElement | null>(null)
const isWelcomeScreen = computed(() => messages.value.length === 0)
const isSidebarOpen = ref(false)
const fileList = ref<any[]>([])
// 生成一个持久的会话ID，如果页面不刷新，ID不变
const currentThreadId = ref(genId())

// ── 会话持久化（2026-10-15，agent3 按钮实测 2.12）：Vite HMR 热更新会重跑 setup，
//    把正在进行的对话整段清空（当轮实测被打断一次）。messages + thread_id 落
//    sessionStorage，重新挂载/刷新时恢复 —— 顺带让 F5 也不丢会话。
//    只存本标签页（sessionStorage 不跨标签）、不落 localStorage；损坏数据按空会话启动。
const CHAT_STORE_KEY = 'p03-chat-session-v1'
function persistChatSession() {
  try {
    sessionStorage.setItem(CHAT_STORE_KEY, JSON.stringify({
      messages: messages.value,
      threadId: currentThreadId.value,
    }))
  } catch { /* 存储满/隐私模式：放弃持久化，不影响主功能 */ }
}
function restoreChatSession() {
  try {
    const raw = sessionStorage.getItem(CHAT_STORE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (Array.isArray(data?.messages) && data.messages.length > 0) {
      messages.value = data.messages
    }
    if (typeof data?.threadId === 'string' && data.threadId) {
      currentThreadId.value = data.threadId
    }
  } catch { /* 损坏数据：忽略 */ }
}
restoreChatSession()
watch(messages, persistChatSession, { deep: true })
watch(currentThreadId, persistChatSession)

// ── API 基址：一律同源相对路径，由 Vite dev server 把 /api、/ws、/outputs 代理到后端
//    （见 vite.config.ts）。彻底移除原先硬编码的 localhost:8000 —— 后端实际监听 8030，
//    旧地址既错端口又锁死主机，是 P03 在平台里跑不通的根因。
const apiBase = '' // 同源
const wsUrl = (threadId: string) => {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}/ws/${threadId}`
}
const fileUrl = (absPath: string) => `${apiBase}/api/download?path=${encodeURIComponent(absPath)}`

// Helper: Scroll to bottom
const scrollToBottom = async () => {
  await nextTick()
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
  }
}

// Fetch Files
const fetchFiles = async () => {
  if (!currentSessionPath.value) return
  try {
    const res = await axios.get(`${apiBase}/api/files`, {
      params: { path: currentSessionPath.value }
    })
    if (res.data.files) {
      fileList.value = res.data.files.map((f: any) => ({
        ...f,
        // 使用新的下载 API，传入绝对路径
        url: fileUrl(f.path)
      }))
    }
  } catch (e) {
    console.error('Failed to fetch files', e)
  }
}

// WebSocket Connection
const connectWebSocket = () => {
  const ws = new WebSocket(wsUrl(currentThreadId.value))

  ws.onopen = () => {
    console.log('WebSocket Connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleSocketMessage(data)
    } catch (e) {
      console.error('Error parsing WS message:', e)
    }
  }

  ws.onclose = () => {
    console.log('WebSocket Disconnected, retrying in 3s...')
    setTimeout(connectWebSocket, 3000)
  }

  socket.value = ws
}

// Handle Incoming Messages
const handleSocketMessage = (data: any) => {
  const { type, event, message, data: eventData } = data

  if (type === 'pong') return

  let lastAiMsg = messages.value.slice().reverse().find(m => m.role === 'ai')
  
  if (event === 'session_created') {
    currentSessionPath.value = eventData.path
    const parts = eventData.path.split(/output[\\/]/)
    if (parts.length > 1) {
      currentSessionUrl.value = `${apiBase}/outputs/${parts[1].replace(/\\/g, '/')}`
    }
    isSidebarOpen.value = true
    fetchFiles()
  } else if (event === 'tool_start') {
    // 触发文件列表刷新，以确保用户能看到生成的文件
    if (currentSessionPath.value) {
      // 延迟一点刷新，因为工具刚开始运行，文件可能还没生成
      // 但如果是“写入文件”类工具，可能很快就有了
      // 这里可以尝试立即刷新 + 延迟刷新
      fetchFiles()
      setTimeout(fetchFiles, 2000)
    }

    if (lastAiMsg) {
      if (!lastAiMsg.logs) lastAiMsg.logs = []
      lastAiMsg.logs.push({
        type: 'tool',
        title: `使用的工具： ${eventData.tool_name}...`,
        details: eventData.args,
        timestamp: new Date().toLocaleTimeString()
      })
      
      if (eventData.args && eventData.args.filename && currentSessionUrl.value) {
        if (!lastAiMsg.files) lastAiMsg.files = []
        const fileUrl = `${currentSessionUrl.value}/${eventData.args.filename}`
        // Avoid duplicates
        if (!lastAiMsg.files.find(f => f.name === eventData.args.filename)) {
           lastAiMsg.files.push({
            name: eventData.args.filename,
            path: eventData.args.filename,
            url: fileUrl
          })
        }
      }
    }
  } else if (event === 'assistant_call') {
    // 同样刷新文件列表
    if (currentSessionPath.value) {
        fetchFiles()
    }
     if (lastAiMsg) {
      if (!lastAiMsg.logs) lastAiMsg.logs = []
      lastAiMsg.logs.push({
        type: 'agent',
        title: `正在使用助手： ${eventData.assistant_name}...`,
        details: eventData.args,
        timestamp: new Date().toLocaleTimeString()
      })
    }
  } else if (event === 'task_result') {
    if (lastAiMsg) {
      lastAiMsg.content = eventData.result
    } else {
       messages.value.push({
        role: 'ai',
        content: eventData.result,
        timestamp: Date.now()
      })
    }
    status.value = 'idle'
    fetchFiles()
  } else if (event === 'error') {
    // 把错误同时写进那条 AI 气泡：content 为空时模板会一直显示「思考中…」，
    // 用户就以为「问数不能回答问题」。
    if (lastAiMsg && !lastAiMsg.content) {
      lastAiMsg.content = `**未能完成本次问数**\n\n${message}`
    }
    messages.value.push({
      role: 'system',
      content: `错误：${message}`,
      timestamp: Date.now()
    })
    status.value = 'idle'
  }
  
  scrollToBottom()
}

// Send Message
const sendMessage = async () => {
  if ((!inputQuery.value.trim() && selectedFiles.value.length === 0) || status.value === 'running') return

  const query = inputQuery.value
  inputQuery.value = ''
  status.value = 'running'

  messages.value.push({
    role: 'user',
    content: query,
    timestamp: Date.now()
  })

  messages.value.push({
    role: 'ai',
    content: '', // Start empty, show "Thinking" via logs/status if needed, or placeholder
    logs: [],
    files: [],
    timestamp: Date.now()
  })

  scrollToBottom()

  // Handle File Upload
  if (selectedFiles.value.length > 0) {
    console.log('Uploading files:', selectedFiles.value)
    
    // Log to UI
    const lastAiMsg = messages.value[messages.value.length - 1]
    if (lastAiMsg && lastAiMsg.role === 'ai') {
        if (!lastAiMsg.logs) lastAiMsg.logs = []
        
        const fileDetails = selectedFiles.value.map(f => ({ name: f.name, size: f.size }))
        
        lastAiMsg.logs.push({
            type: 'info',
            title: `正在上传 ${selectedFiles.value.length} 个文件…`,
            details: fileDetails,
            timestamp: new Date().toLocaleTimeString()
        })
    }

    // Actual Upload
    try {
        const formData = new FormData()
        // Ensure thread_id is available
        if (typeof currentThreadId !== 'undefined' && currentThreadId.value) {
             formData.append('thread_id', currentThreadId.value)
        } else {
             // Fallback if no thread ID (should ideally not happen as initialized in state)
             console.warn('No thread ID found for upload')
        }

        selectedFiles.value.forEach(file => {
            console.log(`Appending file to FormData: name=${file.name}, size=${file.size}, type=${file.type}`)
            formData.append('files', file)
        })

        await axios.post(`${apiBase}/api/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        
        // Clear files after successful upload
        selectedFiles.value = []
        
        if (lastAiMsg && lastAiMsg.logs) {
            lastAiMsg.logs.push({
                type: 'success',
                title: '文件上传成功',
                details: null,
                timestamp: new Date().toLocaleTimeString()
            })
        }

    } catch (e: any) {
        console.error('Upload failed', e)
        if (lastAiMsg && lastAiMsg.logs) {
            lastAiMsg.logs.push({
                type: 'error',
                title: '文件上传失败',
                details: e.message || '未知错误',
                timestamp: new Date().toLocaleTimeString()
            })
        }
        // Don't stop task execution, but maybe warn user?
    }
  }

  try {
    const payload: any = { query }
    // Only add thread_id if it exists and is not empty
    if (typeof currentThreadId !== 'undefined' && currentThreadId.value) {
      payload.thread_id = currentThreadId.value
    }
    console.log('Sending request payload:', payload)
    const res = await axios.post(`${apiBase}/api/task`, payload)
    
    if (res.data && res.data.thread_id) {
      currentThreadId.value = res.data.thread_id
    }
  } catch (error: any) {
    console.error('Request failed:', error)
    let errorMsg = '请求发送失败'
    if (error.message) errorMsg += `（${error.message}）`
    if (error.response && error.response.data) {
        errorMsg += ` 服务端返回：${JSON.stringify(error.response.data)}`
    }
    
    messages.value.push({
      role: 'system',
      content: errorMsg,
      timestamp: Date.now()
    })
    status.value = 'idle'
  }
}

// File Upload
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])

const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    // Append new files to existing list
    selectedFiles.value = [...selectedFiles.value, ...Array.from(target.files)]
    console.log('Files selected:', selectedFiles.value)
    // Reset input so same file can be selected again if needed
    target.value = ''
  }
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

const renderMarkdown = (text: string) => {
  if (!text) return '<span class="typing-indicator">思考中…</span>'
  return marked(text)
}

// ── 数据源健康徽标（2026-10-15，agent3 按钮实测 2.10）：后端 /api/health 早就带了
//    mysql / sql_guard / degraded_reasons，前端此前完全没接。右上角常驻一枚徽标，
//    title 展开明细，每 60s 刷新。任何失败都如实显示"不可用/未知"，不美化。
const healthState = ref<'ok' | 'degraded' | 'down' | 'unknown'>('unknown')
const healthDetail = ref('')
const healthBadge = computed(() => {
  if (healthState.value === 'ok') {
    return { cls: 'ok', text: '● 数据源就绪', title: healthDetail.value || 'GET /api/health 通过' }
  }
  if (healthState.value === 'degraded') {
    return { cls: 'degraded', text: '● 降级', title: healthDetail.value || '部分依赖不可用（详见 /api/health）' }
  }
  if (healthState.value === 'down') {
    return { cls: 'down', text: '● 后端不可用', title: healthDetail.value || 'GET /api/health 失败' }
  }
  return { cls: 'unknown', text: '○ 状态未知', title: '健康检查尚未返回' }
})
async function fetchHealth() {
  try {
    const res = await axios.get(`${apiBase}/api/health`, { timeout: 4000 })
    const d = res.data || {}
    const degraded: string[] = d.degraded_reasons || []
    const mysqlOk = d.mysql?.reachable ? 'MySQL 已连接' : 'MySQL 不可达'
    const guard = `SQL护栏 ${d.sql_guard?.status || '未知'}`
    const e2e = `端到端 ${d.end_to_end?.sql_execute || '未知'}`
    if (d.status === 'ok' && degraded.length === 0) {
      healthState.value = 'ok'
      healthDetail.value = `${mysqlOk} · ${guard} · ${e2e}`
    } else if (d.status === 'ok') {
      healthState.value = 'degraded'
      healthDetail.value = `${mysqlOk} · ${guard} · 降级原因：${degraded.join('；')}`
    } else {
      healthState.value = 'degraded'
      healthDetail.value = `status=${d.status} · ${mysqlOk} · 降级原因：${degraded.join('；') || '无'}`
    }
  } catch (e: any) {
    healthState.value = 'down'
    healthDetail.value = 'GET /api/health 失败：' + (e?.message || String(e))
  }
}

// 首屏性能：WebSocket 非渲染阻塞，但 onMounted 立即建连会抢在首屏资源瀑布之前
// 占一条公网 socket，且后端 WS 不可达时每 3s 重连。延后到首屏空闲后再连，
// 结果推送在用户首次发问时早已就绪（连接是异步的）。不改动收发逻辑。
onMounted(() => {
  fetchHealth()
  setInterval(fetchHealth, 60000)
  const idle = (window as any).requestIdleCallback || ((cb: () => void) => setTimeout(cb, 200))
  idle(() => connectWebSocket())
})
</script>

<template>
  <div class="app-container">
    <!-- Main Content -->
    <main class="main-content" :class="{ 'centered-layout': isWelcomeScreen }">
      
      <!-- Sidebar Toggle Button -->
      <button 
        v-if="currentSessionPath && !isSidebarOpen" 
        class="sidebar-toggle-btn" 
        @click="isSidebarOpen = true"
        title="打开会话文件侧边栏"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <!-- 数据源健康徽标（2026-10-15，2.10）：/api/health 的 mysql/sql_guard/降级原因 就地可视化 -->
      <div class="health-badge" :class="healthBadge.cls" :title="healthBadge.title">{{ healthBadge.text }}</div>

      <!-- Welcome Screen -->
      <div v-if="isWelcomeScreen" class="welcome-screen">
        <div class="welcome-text">
          <h1>欢迎使用问数助手</h1>
          <h2>今天想了解哪方面的经营数据？</h2>
          <!-- 品牌位：公司标与名称由 shared/config/brand.json 下发（外壳 ⚙ 品牌设置里改） -->
          <div class="welcome-brand">
            <span class="cp-brandmark welcome-brand-mark" data-cp-brand="logo">CP</span>
            <span data-cp-brand="company">李奕波个人作品矩阵</span>
          </div>
        </div>
      </div>

      <!-- Chat Area -->
      <div v-else class="chat-scroll-area">
        <div class="chat-container">
          <div v-for="(msg, index) in messages" :key="index" class="message-wrapper" :class="msg.role">
            
            <!-- User Message -->
            <div v-if="msg.role === 'user'" class="message-user">
              <div class="msg-content">{{ msg.content }}</div>
            </div>

            <!-- AI Message -->
            <div v-else-if="msg.role === 'ai'" class="message-ai">
              <div class="ai-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="url(#grad1)"/>
                  <defs>
                    <linearGradient id="grad1" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#1D4ED8"/>
                      <stop offset="1" stop-color="#245AE0"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              
              <div class="ai-content-wrapper">
                <!-- Logs / Thinking Process -->
                <div v-if="msg.logs && msg.logs.length > 0" class="process-section">
                  <details>
                    <summary>
                      <span class="spinner" v-if="status === 'running' && index === messages.length - 1"></span>
                      查看思考过程
                    </summary>
                    <div class="process-steps">
                      <div v-for="(log, idx) in msg.logs" :key="idx" class="step-item">
                        <div class="step-header">
                          <span class="step-icon">🔧</span>
                          <span class="step-title">{{ log.title }}</span>
                        </div>
                        <div class="step-details" v-if="log.details">
                           <pre>{{ JSON.stringify(log.details, null, 2) }}</pre>
                        </div>
                      </div>
                    </div>
                  </details>
                </div>

                <!-- Text Content -->
                <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>

                <!-- Files -->
                <div v-if="msg.files && msg.files.length > 0" class="files-grid">
                  <a v-for="file in msg.files" :key="file.name" :href="file.url" target="_blank" class="file-card" :download="file.name">
                    <div class="file-icon">📄</div>
                    <div class="file-info">
                      <div class="file-name">{{ file.name }}</div>
                      <div class="file-type">文档</div>
                    </div>
                  </a>
                </div>
              </div>
            </div>

            <!-- System Message -->
             <div v-else class="message-system">
              {{ msg.content }}
            </div>

          </div>
          <div ref="messagesEndRef" class="spacer-bottom"></div>
        </div>
      </div>

      <!-- Input Area -->
      <footer class="input-footer">
        <!-- File Preview Tab -->
        <div v-if="selectedFiles.length > 0" class="file-preview-container">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-preview-chip">
            <span class="file-preview-icon">📎</span>
            <span class="file-preview-name">{{ file.name }}</span>
            <button class="file-remove-btn" @click="removeFile(index)" title="移除文件">×</button>
          </div>
        </div>

        <div class="input-container" :class="{ focused: status === 'running' }">
          <input 
            type="file" 
            ref="fileInputRef" 
            multiple
            style="display: none" 
            @change="handleFileChange" 
          />
          <button class="upload-btn" @click="triggerFileUpload" :disabled="status === 'running'" title="上传文件">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <textarea 
            v-model="inputQuery" 
            @keydown.enter.exact.prevent="sendMessage"
            placeholder="请用自然语言描述你的问题，例如：近 30 天各店铺的 GMV 与转化率走势如何？"
            :disabled="status === 'running'"
          ></textarea>
          <button class="send-btn" @click="sendMessage" :disabled="!inputQuery.trim() && status !== 'running'">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
        </div>
        <div class="footer-text">
          AI 生成的问数结果可能存在偏差；结果基于库内只读 SQL，可在「查看思考过程」中核对全部语句与数据来源。
        </div>
      </footer>
    </main>

    <!-- Right Sidebar (File Explorer) -->
    <aside v-if="isSidebarOpen" class="file-sidebar">
      <div class="sidebar-header">
        <h3>会话文件</h3>
        <div style="display: flex; gap: 8px; align-items: center;">
            <button class="folder-btn" @click="fetchFiles" title="刷新文件列表" style="padding: 4px 8px;">
                ↻
            </button>
            <button class="close-btn" @click="isSidebarOpen = false">×</button>
        </div>
      </div>
      <div class="file-list">
        <div v-if="fileList.length === 0" class="empty-files">
          暂无生成文件
        </div>
        <div v-else v-for="file in fileList" :key="file.path" class="file-item">
          <a :href="file.url" target="_blank" class="file-link" :download="file.name">
            <span class="file-icon">📄</span>
            <span class="file-name-text">{{ file.name }}</span>
          </a>
        </div>
      </div>
    </aside>
  </div>
</template>

<style>
/* Global Resets —— 版式/配色令牌的唯一真源是 shared/ui-kit/tokens.css，
   已在 style.css 里 @import 内联；这里只把组件用到的局部变量 re-point 到 --cp-*，
   模块自身不再保留任何独立十六进制色板。 */
:root {
  --bg-dark: var(--cp-bg);
  --surface: var(--cp-surface);
  --elevated: var(--cp-elevated);
  --border-color: var(--cp-line);
  --text-primary: var(--cp-ink1);
  --text-secondary: var(--cp-ink2);
  --accent: var(--cp-brand);
  --accent-hover: var(--cp-brand-hover);
  --user-msg-bg: var(--cp-elevated);
}

body {
  margin: 0;
  background-color: var(--bg-dark);
  color: var(--text-primary);
  font-family: var(--cp-font);
  overflow: hidden; /* App handles scroll */
}

/* Layout */
.app-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  /* justify-content: center; Removed to allow sidebar layout */
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: var(--bg-dark);
  min-width: 0; /* Prevent flex overflow */
}

/* 数据源健康徽标（2.10）：常驻右上、贴侧栏按钮左侧；基础配色走 cp 令牌随主题 */
.health-badge {
  position: absolute;
  top: 1rem;
  right: 4rem;
  z-index: 9;
  font-size: 12px;
  line-height: 1;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--surface);
  color: var(--text-secondary);
  user-select: none;
  white-space: nowrap;
}
.health-badge.ok { color: #16794a; border-color: #b7e4cd; background: #ecfdf5; }
.health-badge.degraded { color: #8a5a00; border-color: #f2e2b0; background: #fffbeb; }
.health-badge.down { color: #b42318; border-color: #f4c2bd; background: #fef1f0; }

.sidebar-toggle-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  z-index: 10;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.sidebar-toggle-btn:hover {
  background: var(--cp-elevated);
  color: var(--text-primary);
}

/* File Sidebar */
.file-sidebar {
  width: 300px;
  background-color: var(--surface);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: var(--text-primary);
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.empty-files {
  color: var(--text-secondary);
  text-align: center;
  font-size: 0.9rem;
  margin-top: 2rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.file-link {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 8px;
  color: var(--text-primary);
  text-decoration: none;
  transition: background 0.2s;
  border: 1px solid transparent;
}

.file-link:hover {
  background: var(--elevated);
  border-color: var(--border-color);
}

.folder-btn {
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.folder-btn:hover {
  background: var(--cp-elevated);
  color: var(--text-primary);
  border-color: var(--text-secondary);
}

.file-name-text {
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Welcome Screen */
.welcome-screen {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 2rem;
}

/* Centered Layout Mode (Initial State) */
.main-content.centered-layout {
  justify-content: center;
  align-items: center;
  overflow-y: auto;
}

.main-content.centered-layout .welcome-screen {
  flex: 0 0 auto;
  padding-bottom: 2rem;
}

.main-content.centered-layout .input-footer {
  width: 100%;
  max-width: 100%;
  padding: 0;
  background: transparent;
  justify-content: center;
}

.welcome-text {
  text-align: center;
  margin-bottom: 2rem;
}

.welcome-text h1 {
  font-size: 3.5rem;
  background: linear-gradient(90deg, var(--accent), var(--accent-hover));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
  line-height: 1.2;
}

.welcome-text h2 {
  font-size: 3.5rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.2;
}

/* 品牌位：字母标/自定义 logo + 公司名 */
.welcome-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 18px;
  font-size: 14px;
  color: var(--text-secondary);
}
.welcome-brand-mark {
  width: 22px;
  height: 22px;
  font-size: 11px;
}
.welcome-brand-mark img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

/* Chat Area */
.chat-scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.chat-container {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
}

/* User Message */
.message-user {
  align-self: flex-end;
  max-width: 70%;
}

.msg-content {
  background-color: var(--user-msg-bg);
  padding: 12px 18px;
  border-radius: 18px;
  border-bottom-right-radius: 4px;
  line-height: 1.6;
}

/* AI Message */
.message-ai {
  align-self: flex-start;
  width: 100%;
  display: flex;
  gap: 1rem;
}

.ai-avatar {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  margin-top: 4px;
}

.ai-content-wrapper {
  flex: 1;
  min-width: 0; /* Text wrap fix */
}

.markdown-body {
  line-height: 1.6;
  font-size: 1rem;
}

.markdown-body pre {
  background: var(--elevated);
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
}

.typing-indicator {
  color: var(--text-secondary);
  font-style: italic;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { opacity: 0.5; }
  50% { opacity: 1; }
  100% { opacity: 0.5; }
}

/* Process / Logs */
.process-section {
  margin-bottom: 1rem;
}

.process-section summary {
  cursor: pointer;
  color: var(--text-secondary);
  font-size: 0.85rem;
  list-style: none; /* Hide default arrow */
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 4px;
}

.process-section summary:hover {
  background: var(--elevated);
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--text-secondary);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.process-steps {
  background: var(--surface);
  border-radius: 8px;
  padding: 0.5rem;
  margin-top: 0.5rem;
  border: 1px solid var(--border-color);
}

.step-item {
  padding: 0.5rem;
  border-left: 2px solid var(--border-color);
  margin-left: 0.5rem;
  margin-bottom: 0.5rem;
}

.step-header {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.step-details pre {
  margin: 0.5rem 0 0 0;
  font-size: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-dark);
  padding: 0.5rem;
  border-radius: 4px;
  overflow-x: auto;
}

/* Files Grid */
.files-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: var(--elevated);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  transition: all 0.2s;
  min-width: 150px;
}

.file-card:hover {
  background: var(--surface);
  border-color: var(--text-secondary);
}

.file-info {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  font-size: 0.9rem;
}

.file-type {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

/* System Message */
.message-system {
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 1rem 0;
}

.spacer-bottom { height: 100px; }

/* Input Footer */
.input-footer {
  background: var(--bg-dark); /* Ensure it covers scrolling content */
  padding: 1rem 2rem 2rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.input-container {
  width: 100%;
  max-width: 800px;
  background: var(--surface);
  border-radius: 32px;
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  transition: background 0.2s;
}

.input-container.focused {
  background: var(--elevated);
}

textarea {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1rem;
  padding: 10px;
  resize: none;
  height: 24px;
  max-height: 200px;
  font-family: inherit;
  outline: none;
}

.send-btn {
  background: none;
  border: none;
  color: var(--text-primary); /* White when active */
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:disabled {
  color: var(--text-secondary);
  cursor: default;
}

.send-btn:not(:disabled):hover {
  background: var(--elevated);
}

.upload-btn {
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 4px;
}

.upload-btn:hover {
  background: var(--elevated);
}

.upload-btn:disabled {
  color: var(--text-secondary);
  cursor: default;
}

.footer-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: center;
}

/* File Preview Styles */
.file-preview-container {
  width: 100%;
  max-width: 800px;
  display: flex;
  justify-content: flex-start;
  padding-left: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.file-preview-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--elevated);
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  font-size: 0.9rem;
  color: var(--text-primary);
  animation: slideUp 0.2s ease-out;
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.file-preview-icon {
  font-size: 1rem;
}

.file-preview-name {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-remove-btn {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0 4px;
  line-height: 1;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-remove-btn:hover {
  background: var(--cp-elevated);
  color: var(--cp-danger);
}

/* Scrollbar Styles */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--cp-elevated);
}
</style>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import tinglanAvatar from './assets/tinglan.webp'
import userProfileAvatar from './assets/userProfileAvatar.svg'

const senderId = ref('u1001')
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)

// [增量 · vibecoding] 版式皮肤：商务（默认）/ 经典，切换后记忆到 localStorage
const SKIN_KEY = 'cs_skin'
const skin = ref(localStorage.getItem(SKIN_KEY) === 'classic' ? 'classic' : 'business')
function applySkin(s) {
  if (typeof document !== 'undefined') {
    document.body.classList.toggle('biz-skin', s === 'business')
  }
}
function toggleSkin() {
  skin.value = skin.value === 'business' ? 'classic' : 'business'
  localStorage.setItem(SKIN_KEY, skin.value)
  applySkin(skin.value)
}
applySkin(skin.value)

const orders = ref([])
const products = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('orders')

// TTS state
const ttsState = ref({})
let currentAudio = null

// Copy state
const copyState = ref({})

// 封面图加载失败登记表（按 URL 记）。
// 商品/订单的 cover_url 是外链（课程数据用的是 placehold.co），网络策略或断网时可能取不到。
// 以前 @error 只把 <img> 藏掉，结果留下一个空灰框；现在改成回退到图标占位。
const failedImages = ref({})
function markImageFailed(url) {
  if (url) failedImages.value[url] = true
}

// 客服数字人配置
const customerService = {
  name: '听澜',
  title: '金牌客服',
  avatar: tinglanAvatar,
  status: '在线'
}

// 用户配置
const userProfile = {
  name: '你',
  avatar: userProfileAvatar
}

// 将消息分组为 Turn 结构
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let turnIndex = 0

  for (const message of messages.value) {
    if (message.type === 'divider') {
      if (currentTurn) {
        result.push(currentTurn)
        currentTurn = null
      }
      result.push({
        type: 'divider',
        text: message.text
      })
      continue
    }

    if (message.role === 'user') {
      // 如果有待处理的当前 turn，先保存
      if (currentTurn) {
        result.push(currentTurn)
      }
      // 创建新的 turn
      turnIndex++
      currentTurn = {
        type: 'turn',
        id: `turn-${turnIndex}`,
        index: turnIndex,
        userMessage: message,
        botMessages: []
      }
    } else if (message.role === 'bot') {
      if (!currentTurn) {
        // 如果没有当前 turn，创建一个（可能是因为历史消息）
        turnIndex++
        currentTurn = {
          type: 'turn',
          id: `turn-${turnIndex}`,
          index: turnIndex,
          userMessage: null,
          botMessages: []
        }
      }
      currentTurn.botMessages.push(message)
    }
  }

  if (currentTurn) {
    result.push(currentTurn)
  }

  return result
})

const chatEndpoint = computed(() => '/api/chat')
const chatHistoryEndpoint = computed(
  () => `/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`
)
const commerceOrdersEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/orders`
)
const commerceProductsEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/products`
)

// LLM 调用慢/网关超时容易出现 HTTP 200 但 body 为空，
// 后端正常响应也可能出现 transient 网络抖动导致空 body；
// 这里用 text + 安全 JSON 解析，避免 response.json() 直接抛 Unexpected end of JSON input。
async function safeParseJson(response) {
  const rawText = await response.text()
  if (!rawText) {
    return null
  }
  try {
    return JSON.parse(rawText)
  } catch (err) {
    // 当成不可解析的字符串返回，让上层用 response.status 报错
    return { __raw: rawText }
  }
}

// 后端聊天一次平均 5~10s（取决于 LLM 与流程推进深度），但偶发 30s+；
// 60s 仍超时说明后端真的卡了，前端不再僵等
const CHAT_REQUEST_TIMEOUT_MS = 60 * 1000

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
  }
}

function appendUserText(text) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
  })
}

function appendUserObject(objectType, payload) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    // 对象卡有两种来源、两种形状：
    //   实时消息：payload 是扁平业务对象（cover_url / status / amount 直接在顶层）
    //   历史消息：payload 是 { type, id, title, attributes: { ... } }
    // 模板只按扁平形状取值，所以历史卡会丢封面图、状态也退化成文字。
    // 这里统一把 attributes 摊平合并，两种来源在模板里就一致了。
    const object = message.object
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: object.type,
      payload: { ...(object.attributes ?? {}), ...object },
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = ['user', 'bot', 'divider'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

function resetConversation() {
  messages.value = []
  errorMessage.value = ''
}

// 商务人性化增量：一键导出当前会话为文本（纯前端，不依赖后端接口）
function exportConversation() {
  if (!messages.value.length) {
    errorMessage.value = '当前没有可导出的对话内容。'
    return
  }
  const lines = messages.value.map((message) => {
    if (message.type === 'divider') {
      return `—— ${message.text ?? '以上为历史消息'} ——`
    }
    const who = message.role === 'user' ? '用户' : message.role === 'bot' ? customerService.name : '系统'
    if (message.type === 'object') {
      const kind = message.objectType === 'order' ? '订单' : '商品'
      return `${who}：[${kind}] ${getObjectTitle(message)}`
    }
    return `${who}：${message.text ?? ''}`
  })
  const content = `电商客服对话记录\n导出时间：${new Date().toLocaleString()}\n\n${lines.join('\n')}`
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `客服对话_${Date.now()}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

function formatOrderSummary(order) {
  return order.status ? `订单状态：${order.status}` : '订单'
}

const ORDER_STATUS_CLASS = {
  '待发货': 'status-warning',
  '待揽收': 'status-warning',
  '运输中': 'status-info',
  '派送中': 'status-info',
  '已完成': 'status-success',
  '已签收': 'status-success',
  '已取消': 'status-muted',
  '退款中': 'status-danger',
  '已退款': 'status-muted',
}

function getStatusClass(status) {
  return ORDER_STATUS_CLASS[status] || 'status-muted'
}

function formatProductSummary(product) {
  if (product.description) {
    return product.description
  }
  if (product.attributes?.price) {
    return `商品价格：${formatAmount(product.attributes.price)}`
  }
  return '商品信息'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return message.objectType === 'order' ? '订单对象' : '商品对象'
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.order_id ?? payload.product_id ?? payload.id
  const label = message.objectType === 'order' ? '订单号' : '商品号'
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'order') {
    const status = payload.status ?? payload.attributes?.status
    return status ? `订单状态：${status}` : '订单'
  }
  return formatProductSummary(payload)
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  const amount = message.objectType === 'order'
    ? payload.amount ?? payload.attributes?.amount
    : payload.price ?? payload.attributes?.price
  return formatAmount(amount)
}

async function fetchSidebarData() {
  const currentSenderId = senderId.value.trim()
  orders.value = []
  products.value = []
  sidebarError.value = ''

  if (!currentSenderId) {
    return
  }

  isLoadingSidebar.value = true
  try {
    const [ordersResponse, productsResponse] = await Promise.all([
      fetch(commerceOrdersEndpoint.value),
      fetch(commerceProductsEndpoint.value),
    ])

    const [ordersPayload, productsPayload] = await Promise.all([
      safeParseJson(ordersResponse),
      safeParseJson(productsResponse),
    ])

    if (!ordersResponse.ok) {
      throw new Error(ordersPayload?.detail || '加载订单列表失败。')
    }
    if (!productsResponse.ok) {
      throw new Error(productsPayload?.detail || '加载商品列表失败。')
    }

    orders.value = Array.isArray(ordersPayload?.data?.orders) ? ordersPayload.data.orders : []
    products.value = Array.isArray(productsPayload?.data?.products) ? productsPayload.data.products : []
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : '加载右侧列表失败。'
  } finally {
    isLoadingSidebar.value = false
  }
}

async function fetchChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(chatHistoryEndpoint.value)
    const data = await safeParseJson(response)
    if (!response.ok) {
      throw new Error(data?.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载历史消息失败。'
  }
}

async function sendPayload(payload) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  isSending.value = true

  // 后端慢导致浏览器/Vite 代理把请求挂死很常见，60s 超时后给用户明确提示而不是无声卡住
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), CHAT_REQUEST_TIMEOUT_MS)

  try {
    const response = await fetch(chatEndpoint.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender_id: senderId.value.trim(),
        ...payload,
      }),
      signal: controller.signal,
    })

    // HTTP 200 但 body 为空 = 后端/Vite 代理被中间层截断；
    // 显式提示而不是闷头让 .json() 抛 Unexpected end of JSON input
    if (response.status === 200) {
      const raw = await response.text()
      if (!raw) {
        throw new Error('后端返回了空响应，请稍后重试。')
      }
      let data
      try {
        data = JSON.parse(raw)
      } catch (err) {
        throw new Error('后端返回的内容不是合法 JSON。')
      }
      appendBotMessages(data.messages ?? [])
      // 文字气泡上屏的同时，让数字人同步朗读本轮回复（未连接时内部自动跳过）
      speakBotReply(data.messages ?? [])
    } else {
      const data = await safeParseJson(response)
      throw new Error(data?.detail || `请求失败（HTTP ${response.status}）。`)
    }
  } catch (error) {
    if (error?.name === 'AbortError') {
      errorMessage.value = `请求超时（${CHAT_REQUEST_TIMEOUT_MS / 1000}s）。后端可能仍在生成回复，请稍后重试。`
    } else {
      errorMessage.value = error instanceof Error ? error.message : '请求失败。'
    }
  } finally {
    clearTimeout(timeoutId)
    isSending.value = false
  }
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}
async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendOrder(order) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }

  appendUserObject('order', { ...order })
  await sendPayload({
    object: {
      type: 'order',
      id: order.order_id,
      title: order.title,
      attributes: {
        status: order.status,
        amount: order.amount,
        created_at: order.created_at,
        cover_url: order.cover_url,
      },
    },
  })
}

async function sendProduct(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }

  appendUserObject('product', { ...product })
  await sendPayload({
    object: {
      type: 'product',
      id: product.product_id,
      title: product.title,
      attributes: {
        price: product.price,
        cover_url: product.cover_url,
        description: product.description,
      },
    },
  })
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) {
      return
    }

    resetConversation()
    if (!value) {
      orders.value = []
      products.value = []
      return
    }
    await Promise.all([fetchSidebarData(), fetchChatHistory()])
  }
)

onMounted(async () => {
  await Promise.all([fetchSidebarData(), fetchChatHistory()])
})

onUnmounted(() => {
  // 组件卸载要断开数字人：否则服务端房间不释放，再次进入会撞并发上限
  disconnectDigitalHuman()
})

async function playTts(botMsg) {
  const msgId = botMsg.id
  if (!botMsg.text || ttsState.value[msgId] === 'loading') return

  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  for (const key of Object.keys(ttsState.value)) {
    if (ttsState.value[key] === 'playing') ttsState.value[key] = 'idle'
  }

  ttsState.value[msgId] = 'loading'
  try {
    const response = await fetch('/api/chat/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: botMsg.text }),
    })
    if (!response.ok) throw new Error('TTS 请求失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    ttsState.value[msgId] = 'playing'
    currentAudio.onended = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    currentAudio.onerror = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    await currentAudio.play()
  } catch (error) {
    ttsState.value[msgId] = 'idle'
    console.error('TTS error:', error)
  }
}

async function copyBotText(botMsg) {
  const msgId = botMsg.id
  try {
    await navigator.clipboard.writeText(botMsg.text)
    copyState.value[msgId] = true
    setTimeout(() => { copyState.value[msgId] = false }, 1800)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}

// ── 数字人（魔珐星云）────────────────────────────────────────────────
// 设计要点：
// · 数字人画面由魔珐星云 SDK 全权渲染，后端只负责下发凭证，前端不存任何密钥
// · 默认不连接，用户点「连接数字人」才动态加载 SDK，首屏不受外部脚本影响
// · 客服回复到达时自动调用 speak()，与文字气泡同步朗读
const XMOV_SDK_URL = 'https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js'

// 数字人连接状态机：idle 未连接 / loading 连接中 / ready 已就绪 / error 失败
const digitalHuman = ref({
  status: 'idle',
  progress: 0,
  message: '数字人未连接',
})

// SDK 实例与脚本加载句柄都放在组件闭包外，避免被 Vue 响应式代理包住
let liteSDK = null
let sdkScriptPromise = null

const digitalHumanButtonLabel = computed(() => {
  if (digitalHuman.value.status === 'loading') return '连接中…'
  if (digitalHuman.value.status === 'ready') return '断开数字人'
  return '连接数字人'
})

// 按需加载官方 SDK：加载过一次就复用同一个 Promise，不会重复插脚本
function loadXmovSdk() {
  if (window.XmovAvatar) return Promise.resolve()
  if (sdkScriptPromise) return sdkScriptPromise

  sdkScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = XMOV_SDK_URL
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      // 失败要清掉缓存句柄，否则用户重试时拿到的是已失败的 Promise
      sdkScriptPromise = null
      reject(new Error('数字人 SDK 加载失败，请检查网络后重试'))
    }
    document.head.appendChild(script)
  })
  return sdkScriptPromise
}

// 断开并复位：destroy 释放服务端房间，避免触发并发限制（错误码 10005）
function disconnectDigitalHuman() {
  if (liteSDK) {
    try {
      liteSDK.destroy()
    } catch (error) {
      // 实例可能已经不存在，销毁异常可以直接忽略
      console.warn('[数字人] 销毁异常：', error)
    }
    liteSDK = null
  }
  digitalHuman.value.status = 'idle'
  digitalHuman.value.progress = 0
  digitalHuman.value.message = '数字人未连接'
}

// 连接数字人：取凭证 → 载 SDK → 建实例 → init 下载资源到 100%
async function connectDigitalHuman() {
  // 连接中不响应重复点击
  if (digitalHuman.value.status === 'loading') return
  // 已连接时同一个按钮转为「断开」
  if (liteSDK) {
    disconnectDigitalHuman()
    return
  }

  digitalHuman.value.status = 'loading'
  digitalHuman.value.progress = 0
  digitalHuman.value.message = '正在获取数字人凭证…'

  // 凭证必须向后端要：AppSecret 只存在于后端 .env，前端源码里不留明文
  let credential
  try {
    const response = await fetch('/api/digital-human/credentials')
    const data = await safeParseJson(response)
    if (!response.ok) {
      throw new Error(data?.detail || `获取凭证失败（HTTP ${response.status}）`)
    }
    credential = data
  } catch (error) {
    digitalHuman.value.status = 'error'
    digitalHuman.value.message = error instanceof Error ? error.message : '获取数字人凭证失败'
    return
  }

  digitalHuman.value.message = '正在加载数字人资源…'
  try {
    await loadXmovSdk()
  } catch (error) {
    digitalHuman.value.status = 'error'
    digitalHuman.value.message = error instanceof Error ? error.message : '数字人 SDK 加载失败'
    return
  }

  liteSDK = new window.XmovAvatar({
    containerId: '#digital-human-sdk',
    appId: credential.app_id,
    appSecret: credential.app_secret,
    gatewayServer: credential.gateway_server,
    hardwareAcceleration: 'prefer-hardware',
    enableLogger: false,
    onMessage(message) {
      // 50001/50002 是在线/离线模式切换，属正常事件，不算错误
      if (message && message.code && message.code !== 50001 && message.code !== 50002) {
        digitalHuman.value.message = `数字人异常（code ${message.code}）`
      }
    },
    onVoiceStateChange(status) {
      // 说话期间给出明确反馈，让用户知道数字人正在工作
      if (digitalHuman.value.status !== 'ready') return
      digitalHuman.value.message = status === 'start' ? `${customerService.name}正在说话…` : '数字人在线'
    },
  })

  // 不同 SDK 版本方法名有差异（init / startSession），按实际实例挑一个可用入口
  const startMethod = typeof liteSDK.init === 'function' ? 'init' : 'startSession'
  liteSDK[startMethod]({
    initModel: 'normal',
    onDownloadProgress(progress) {
      digitalHuman.value.progress = progress
      // 资源没下完就 speak 是无效的，必须等进度到 100%
      if (progress >= 100) {
        digitalHuman.value.status = 'ready'
        digitalHuman.value.message = '数字人在线'
      }
    },
  })
}

// 驱动数字人朗读一段文本
function speakByDigitalHuman(text) {
  const content = (text || '').trim()
  if (!content) return
  // 没连上或还在加载就静默跳过，不打断正常聊天
  if (!liteSDK || digitalHuman.value.status !== 'ready') return

  try {
    // 官方建议：上一次以 is_end=true 结束后再 speak，中间用 interactiveidle 切一次状态，
    // 否则口型容易对不上；同时它也起到"打断上一句"的作用
    liteSDK.interactiveidle()
    // 非流式整句朗读：第三参 is_end=true 表示这句话说完了
    liteSDK.speak(content, true, true)
  } catch (error) {
    console.warn('[数字人] 朗读失败：', error)
  }
}

// 把本轮所有机器人文本合并成一段交给数字人朗读（对象卡片消息没有文本，跳过）
function speakBotReply(botMessages) {
  const text = (botMessages || [])
    .filter((message) => message && message.text)
    .map((message) => String(message.text).trim())
    .filter(Boolean)
    .join(' ')
  speakByDigitalHuman(text)
}
</script>

<template>
  <div class="app-shell">
    <!-- [增量] 版式皮肤切换：商务（默认）⇄ 经典 -->
    <button type="button" class="skin-toggle" title="切换版式：商务 / 经典" @click="toggleSkin">
      ◈ {{ skin === 'business' ? '商务版式' : '经典版式' }}
    </button>
    <div class="workspace">
      <!-- 数字人区域（聊天框左侧）：默认不连接，点按钮才加载 SDK -->
      <aside class="digital-human-card">
        <header class="digital-human-header">
          <div class="digital-human-title">
            <span class="digital-human-dot" :class="`is-${digitalHuman.status}`"></span>
            <h2>数字人</h2>
          </div>
          <span class="digital-human-badge">{{ customerService.name }}</span>
        </header>

        <div class="digital-human-body">
          <!-- 舞台用定位壳包住，让占位层能精确盖在画面上 -->
          <div class="digital-human-stage-wrap">
            <!-- SDK 渲染容器：必须有明确宽高，否则画面画不出来 -->
            <div id="digital-human-sdk" class="digital-human-stage"></div>

            <!-- 未就绪时盖一层占位：头像 + 状态 + 加载进度 -->
            <div v-if="digitalHuman.status !== 'ready'" class="digital-human-overlay">
              <div class="digital-human-avatar-wrapper" :class="{ 'is-loading': digitalHuman.status === 'loading' }">
                <img :src="customerService.avatar" class="digital-human-avatar" alt="数字人" />
              </div>
              <p class="digital-human-hint">{{ digitalHuman.message }}</p>
              <div v-if="digitalHuman.status === 'loading'" class="digital-human-progress">
                <div class="digital-human-progress-track">
                  <div class="digital-human-progress-bar" :style="{ width: `${digitalHuman.progress}%` }"></div>
                </div>
                <span class="digital-human-progress-text">{{ digitalHuman.progress }}%</span>
              </div>
              <p v-else-if="digitalHuman.status === 'idle'" class="digital-human-tip">
                连接后由数字人朗读客服回复
              </p>
            </div>
          </div>
        </div>

        <footer class="digital-human-footer">
          <button
            type="button"
            class="digital-human-button"
            :class="{ 'is-connected': digitalHuman.status === 'ready' }"
            :disabled="digitalHuman.status === 'loading'"
            @click="connectDigitalHuman"
          >
            {{ digitalHumanButtonLabel }}
          </button>
          <p class="digital-human-status">{{ digitalHuman.message }}</p>
        </footer>
      </aside>

      <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <div class="header-info">
              <h1>电商客服系统</h1>
              <!-- 公司名与 logo 由 shared/config/brand.json 下发（外壳 ⚙ 品牌设置里改） -->
              <div class="header-brand">
                <span class="cp-brandmark header-brand-mark" data-cp-brand="logo">CS</span>
                <span class="header-brand-name" data-cp-brand="company">李奕波个人作品矩阵</span>
              </div>
              <div class="service-info">
                <div class="service-avatar-wrapper">
                  <img :src="customerService.avatar" class="service-avatar" />
                  <span class="status-indicator"></span>
                </div>
                <div class="service-details">
                  <span class="service-name">{{ customerService.name }}</span>
                  <span class="service-status">{{ customerService.status }}</span>
                </div>
              </div>
            </div>
            <button type="button" class="clear-button export-button" title="导出当前对话" @click="exportConversation">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>导出</span>
            </button>
            <button type="button" class="clear-button" title="清空对话" @click="resetConversation">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="21 3 21 9 15 9" />
                <path d="M21 12a9 9 0 1 1-2.64-6.36L21 9" />
              </svg>
              <span>新对话</span>
            </button>
          </div>
        </header>

        <section class="controls">
          <label class="field">
            <span>用户标识</span>
            <div class="field-row">
              <input v-model="senderId" type="text" placeholder="u1001" />
              <button
                type="button"
                class="secondary-button"
                :disabled="isLoadingSidebar"
                @click="fetchSidebarData"
              >
                {{ isLoadingSidebar ? '加载中...' : '刷新对象列表' }}
              </button>
            </div>
          </label>
        </section>

        <section ref="messagesContainer" class="messages">
          <div v-if="turns.length === 0" class="welcome">
            <div class="welcome-card">
              <div class="welcome-glow"></div>
              <div class="welcome-avatar-wrapper">
                <img :src="customerService.avatar" class="welcome-avatar" alt="听澜" />
                <span class="welcome-status-pulse"></span>
              </div>
              <h2 class="welcome-greeting">Hi，我是 {{ customerService.name }}</h2>
              <p class="welcome-subtitle">你的专属电商客服，随时为你服务</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in ['我要退款', '查订单状态', '商品推荐', '退换货政策']"
                  :key="chip"
                  type="button"
                  class="welcome-chip"
                  :disabled="isSending"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
                  文字对话
                </span>
                <span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M15.54 8.46a5 5 0 0 1 0 7.07" /></svg>
                  语音播报
                </span>
                <span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
                  订单查询
                </span>
                <span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>
                  商品咨询
                </span>
              </p>
            </div>
          </div>

          <!-- Turn 结构展示 -->
          <template v-for="(item, index) in turns" :key="item.id || index">
            <!-- 分隔线 -->
            <div v-if="item.type === 'divider'" class="history-divider">
              <span>{{ item.text }}</span>
            </div>

            <!-- Turn 卡片 -->
            <div v-else class="turn-card" :class="{ 'has-user-message': item.userMessage }">
              <!-- Turn 标识 -->
              <div class="turn-header">
                <span class="turn-badge">对话 #{{ item.index }}</span>
              </div>

              <!-- 用户消息区域 -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-header">
                  <div class="avatar-wrapper user-avatar">
                    <img :src="userProfile.avatar" class="avatar" />
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ userProfile.name }}</span>
                    <span class="agent-label">用户</span>
                  </div>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div class="object-card" :class="`object-card-${item.userMessage.objectType}`">
                      <div class="object-card-badge">
                        {{ item.userMessage.objectType === 'order' ? '订单对象' : '商品对象' }}
                      </div>
                      <img
                        v-if="item.userMessage.type === 'object' && item.userMessage.payload.cover_url && !failedImages[item.userMessage.payload.cover_url]"
                        :src="item.userMessage.payload.cover_url"
                        :alt="getObjectTitle(item.userMessage)"
                        class="object-card-image"
                        @error="markImageFailed(item.userMessage.payload.cover_url)"
                      />
                      <div class="object-card-title">{{ getObjectTitle(item.userMessage) }}</div>
                      <div class="object-card-meta">{{ getObjectIdentifier(item.userMessage) }}</div>
                      <div class="object-card-meta">
                        <span v-if="item.userMessage.objectType === 'order' && item.userMessage.payload.status" class="status-badge" :class="getStatusClass(item.userMessage.payload.status)">{{ item.userMessage.payload.status }}</span>
                        <span v-else>{{ getObjectSummary(item.userMessage) }}</span>
                      </div>
                      <div class="object-card-price">{{ getObjectAmount(item.userMessage) }}</div>
                    </div>
                  </template>
                  <template v-else>
                    <p>{{ item.userMessage.text }}</p>
                  </template>
                </div>
              </div>

              <!-- 客服回复区域 -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-header">
                  <div class="avatar-wrapper service-avatar">
                    <img :src="customerService.avatar" class="avatar" />
                    <span class="status-dot"></span>
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ customerService.name }}</span>
                    <span class="agent-label">{{ customerService.title }}</span>
                  </div>
                </div>
                <div class="bot-messages">
                  <div
                    v-for="(botMsg, msgIndex) in item.botMessages"
                    :key="msgIndex"
                    class="turn-bubble bot-bubble"
                  >
                    <template v-if="botMsg.type === 'object'">
                      <div class="object-card" :class="`object-card-${botMsg.objectType}`">
                        <div class="object-card-badge">
                          {{ botMsg.objectType === 'order' ? '订单对象' : '商品对象' }}
                        </div>
                        <img
                          v-if="botMsg.type === 'object' && botMsg.payload.cover_url && !failedImages[botMsg.payload.cover_url]"
                          :src="botMsg.payload.cover_url"
                          :alt="getObjectTitle(botMsg)"
                          class="object-card-image"
                          @error="markImageFailed(botMsg.payload.cover_url)"
                        />
                        <div class="object-card-title">{{ getObjectTitle(botMsg) }}</div>
                        <div class="object-card-meta">{{ getObjectIdentifier(botMsg) }}</div>
                        <div class="object-card-meta">
                          <span v-if="botMsg.objectType === 'order' && botMsg.payload.status" class="status-badge" :class="getStatusClass(botMsg.payload.status)">{{ botMsg.payload.status }}</span>
                          <span v-else>{{ getObjectSummary(botMsg) }}</span>
                        </div>
                        <div class="object-card-price">{{ getObjectAmount(botMsg) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="bot-text-row">
                        <p>{{ botMsg.text }}</p>
                        <div class="bot-actions">
                          <button type="button" class="tts-button"
                            :class="{ 'tts-loading': ttsState[botMsg.id] === 'loading', 'tts-playing': ttsState[botMsg.id] === 'playing' }"
                            :disabled="ttsState[botMsg.id] === 'loading'"
                            :title="ttsState[botMsg.id] === 'playing' ? '正在播放...' : '语音播报'"
                            @click.stop="playTts(botMsg)">
                            <span v-if="ttsState[botMsg.id] === 'loading'" class="tts-spinner"></span>
                            <span v-else-if="ttsState[botMsg.id] === 'playing'" class="tts-bars">
                              <span></span><span></span><span></span>
                            </span>
                            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                            </svg>
                          </button>
                          <button type="button" class="copy-button"
                            :class="{ 'copy-done': copyState[botMsg.id] }"
                            :title="copyState[botMsg.id] ? '已复制' : '复制文字'"
                            @click.stop="copyBotText(botMsg)">
                            <svg v-if="copyState[botMsg.id]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                              <rect x="9" y="9" width="12" height="12" rx="2" />
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </template>
                    <div v-if="botMsg.suggestions && botMsg.suggestions.length > 0" class="suggestion-chips">
                      <button
                        v-for="sug in botMsg.suggestions"
                        :key="sug"
                        type="button"
                        class="suggestion-chip"
                        :disabled="isSending"
                        @click.stop="sendSuggestion(sug)"
                      >{{ sug }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </section>

        <div v-if="isSending" class="typing-indicator">
          <div class="typing-avatar">
            <img :src="customerService.avatar" class="avatar-small" alt="听澜" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">听澜正在输入...</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            type="text"
            placeholder="请输入咨询内容..."
            :disabled="isSending"
          />
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? '发送中...' : '发送' }}
          </button>
        </form>
      </div>

      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>业务对象</h2>
        </div>

        <div class="tabs">
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'orders' }"
            @click="activeTab = 'orders'"
          >
            订单
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'products' }"
            @click="activeTab = 'products'"
          >
            商品
          </button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <div v-if="activeTab === 'orders'" class="sidebar-list">
          <div v-if="!orders.length && !isLoadingSidebar" class="sidebar-empty">
            暂无订单数据
          </div>

          <article v-for="order in orders" :key="order.order_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="order.cover_url && !failedImages[order.cover_url]"
                :src="order.cover_url"
                :alt="order.title"
                class="card-image"
                @error="markImageFailed(order.cover_url)"
              />
              <div v-else class="card-image-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" /></svg>
              </div>
            </div>
            <div class="card-top">
              <div class="card-title">{{ order.title }}</div>
              <div class="card-amount">{{ formatAmount(order.amount) }}</div>
            </div>
            <div class="card-meta">订单号：{{ order.order_id }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="getStatusClass(order.status)">{{ order.status }}</span>
            </div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendOrder(order)"
            >
              发送订单
            </button>
          </article>
        </div>

        <div v-else class="sidebar-list">
          <div v-if="!products.length && !isLoadingSidebar" class="sidebar-empty">
            暂无商品数据
          </div>

          <article v-for="product in products" :key="product.product_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="product.cover_url && !failedImages[product.cover_url]"
                :src="product.cover_url"
                :alt="product.title"
                class="card-image"
                @error="markImageFailed(product.cover_url)"
              />
              <div v-else class="card-image-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" /><line x1="3" y1="6" x2="21" y2="6" /><path d="M16 10a4 4 0 0 1-8 0" /></svg>
              </div>
            </div>
            <div class="card-top">
              <div class="card-title">{{ product.title }}</div>
              <div class="card-amount">{{ formatAmount(product.price) }}</div>
            </div>
            <div class="card-meta">商品号：{{ product.product_id }}</div>
            <div class="card-meta">商品信息：最近浏览 / 购买商品</div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendProduct(product)"
            >
              发送商品
            </button>
          </article>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* ══════════════════════════════════════════════════════════════════════
   统一深色主题（Li Yibo's Personal Portfolio 设计规范）
   ──────────────────────────────────────────────────────────────────────
   设计原则：
     1. 深灰底 + 层次分明，靠「边框 + 微投影」分层
     2. 主色 #3370FF（蓝），暖色仅用于价格/待办语义
     3. 动效克制：只保留必要的进入动画与状态指示
     4. 数字人竖版舞台比例仍由 .digital-human-card 的 --dh-stage-ratio 统一控制
   ══════════════════════════════════════════════════════════════════════ */

:global(*) {
  box-sizing: border-box;
}

:global(:root) {
  /* ── 页面底色与层次（re-point 到平台令牌，模块不再自持色板） ── */
  --color-bg: var(--cp-bg);
  --color-bg-soft: var(--cp-bg);
  --color-surface: var(--cp-surface);
  --color-surface-2: var(--cp-bg);
  --color-surface-3: var(--cp-elevated);
  --color-surface-field: var(--cp-elevated);
  /* ── 文字（深底浅字） ── */
  --color-text-primary: var(--cp-ink1);
  --color-text-secondary: var(--cp-ink2);
  --color-text-muted: var(--cp-ink3);
  --color-text-inverse: var(--cp-bg);
  /* ── 主色：蓝色（唯一强调色）+ 其 alpha 变体一律由令牌 color-mix 派生 ── */
  --color-accent: var(--cp-brand);
  --color-accent-strong: var(--cp-brand);
  --color-accent-soft: color-mix(in srgb, var(--cp-brand) 12%, transparent);
  --color-accent-soft-bg: color-mix(in srgb, var(--cp-brand) 7%, transparent);
  --color-accent-tint: color-mix(in srgb, var(--cp-brand) 10%, transparent);
  --color-accent-glow: color-mix(in srgb, var(--cp-brand) 20%, transparent);
  /* ── 暖色：价格 / 待发货语义 → 平台 warning ── */
  --color-warm: var(--cp-warning);
  --color-warm-strong: var(--cp-warning);
  --color-warm-soft: color-mix(in srgb, var(--cp-warning) 12%, transparent);
  /* ── 语义色（对齐平台令牌） ── */
  --color-success: var(--cp-success);
  --color-success-soft: color-mix(in srgb, var(--cp-success) 14%, transparent);
  --color-info: var(--cp-info);
  --color-info-soft: color-mix(in srgb, var(--cp-info) 12%, transparent);
  --color-danger: var(--cp-danger);
  --color-danger-soft: color-mix(in srgb, var(--cp-danger) 14%, transparent);
  /* ── 边框 ── */
  --color-border: var(--cp-line);
  --color-border-light: var(--cp-line);
  --color-border-strong: color-mix(in srgb, var(--cp-line) 55%, var(--cp-ink3));
  /* 注：rgba(51,112,255,…) 的气泡/卡片渐变属于强调色 alpha 底，仍与 --cp-brand 同族；
     个别 inline SVG 渐变 stop 保留十六进制（属性不支持 var()），值即品牌蓝本身。 */
  /* ── 圆角 ── */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --radius-full: 9999px;
  /* ── 投影：深色主题需要更强的阴影来体现层次 ── */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.25);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.25), 0 2px 8px rgba(0, 0, 0, 0.20);
  --shadow-md: 0 2px 4px rgba(0, 0, 0, 0.25), 0 8px 24px rgba(0, 0, 0, 0.25);
  --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.35);
  --shadow-focus: 0 0 0 3px rgba(51, 112, 255, 0.25);
  /* ── 过渡 ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 140ms;
  --duration-base: 220ms;
}

:global(body) {
  margin: 0;
  font-family: var(--cp-font);
  background: var(--color-bg);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(button),
:global(input) {
  font: inherit;
}

:global(#app) {
  min-height: 100vh;
}

:global(:focus-visible) {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* ── 页面外壳 ─────────────────────────────────────────────────────── */
.app-shell {
  min-height: 100vh;
  padding: 20px;
  position: relative;
  background:
    radial-gradient(1100px 520px at 12% -8%, rgba(51, 112, 255, 0.06), transparent 62%),
    radial-gradient(980px 480px at 96% 106%, rgba(51, 112, 255, 0.04), transparent 60%),
    var(--color-bg);
}

.workspace {
  width: min(1880px, 100%);
  margin: 0 auto;
  display: grid;
  /* 三卡横向：两侧卡片要能读完订单标题与价格，聊天区不需要占满剩余宽度 */
  grid-template-columns: clamp(280px, 22vw, 420px) minmax(0, 1fr) clamp(288px, 23vw, 430px);
  gap: 20px;
  position: relative;
  z-index: 1;
}

.chat-card,
.sidebar,
.digital-human-card {
  min-height: calc(100vh - 40px);
  height: calc(100vh - 40px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow var(--duration-base) var(--ease-out-expo),
    border-color var(--duration-base) var(--ease-out-expo);
}

.chat-card,
.sidebar,
.digital-human-card {
  display: flex;
  flex-direction: column;
}

.chat-card:hover,
.sidebar:hover,
.digital-human-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-border-strong);
}

/* ══ 数字人面板（聊天框左侧） ════════════════════════════════════════ */
.digital-human-card {
  --dh-stage-ratio: 9 / 16;
}

.digital-human-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.digital-human-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.digital-human-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--color-text-primary);
}

.digital-human-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted);
  transition: background var(--duration-base) linear, box-shadow var(--duration-base) linear;
}
.digital-human-dot.is-loading {
  background: var(--color-warm);
  box-shadow: 0 0 0 3px var(--color-warm-soft);
  animation: dhPulse 1.5s ease-in-out infinite;
}
.digital-human-dot.is-ready {
  background: var(--color-success);
  box-shadow: 0 0 0 3px var(--color-success-soft);
}
.digital-human-dot.is-error {
  background: var(--color-danger);
  box-shadow: 0 0 0 3px var(--color-danger-soft);
}
@keyframes dhPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.digital-human-badge {
  font-size: 11.5px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  color: var(--color-accent);
  background: var(--color-accent-tint);
}

.digital-human-body {
  position: relative;
  flex: 1;
  min-height: 0;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  overflow-y: auto;
  scrollbar-width: none;
  background: var(--color-surface-2);
}
.digital-human-body::-webkit-scrollbar {
  display: none;
}

.digital-human-stage-wrap {
  position: relative;
  width: 100%;
}

.digital-human-stage {
  width: 100%;
  aspect-ratio: var(--dh-stage-ratio);
  border-radius: var(--radius-md);
  background: linear-gradient(180deg, var(--cp-elevated) 0%, var(--cp-bg) 100%);
  border: 1px solid var(--color-border);
  overflow: hidden;
}
.digital-human-stage:empty {
  box-shadow: inset 0 0 0 1px rgba(51, 112, 255, 0.06),
    inset 0 12px 40px rgba(0, 0, 0, 0.15);
}

.digital-human-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 0 18px;
  text-align: center;
  pointer-events: none;
}

.digital-human-avatar-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  padding: 3px;
  background: var(--color-surface-3);
  border: 1px solid var(--color-border-strong);
  box-shadow: var(--shadow-sm);
}
.digital-human-avatar-wrapper::after {
  content: "";
  position: absolute;
  inset: -22px;
  border-radius: 50%;
  border: 1px dashed var(--color-border-strong);
}
.digital-human-avatar-wrapper.is-loading {
  animation: dhBreathe 2.2s ease-in-out infinite;
}
@keyframes dhBreathe {
  0%, 100% { transform: scale(1); opacity: 0.92; }
  50% { transform: scale(1.04); opacity: 1; }
}
.digital-human-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.digital-human-hint {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-secondary);
}
.digital-human-tip {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-muted);
}

.digital-human-progress {
  width: 100%;
  max-width: 190px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.digital-human-progress-track {
  width: 100%;
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--color-bg-soft);
  overflow: hidden;
}
.digital-human-progress-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-accent);
  transition: width var(--duration-base) linear;
}
.digital-human-progress-text {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.digital-human-footer {
  padding: 14px 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-surface);
}
.digital-human-button {
  width: 100%;
  padding: 11px 16px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: var(--color-accent);
  color: #ffffff;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--duration-fast) linear, box-shadow var(--duration-fast) linear,
    transform var(--duration-fast) var(--ease-out-expo);
}
.digital-human-button:hover:not(:disabled) {
  background: var(--color-accent-strong);
  box-shadow: 0 6px 16px var(--color-accent-glow);
}
.digital-human-button:active:not(:disabled) {
  transform: translateY(1px);
  box-shadow: none;
}
.digital-human-button:disabled {
  cursor: progress;
  opacity: 0.6;
}
.digital-human-button.is-connected {
  background: var(--color-surface);
  border-color: var(--color-border-strong);
  color: var(--color-text-secondary);
}
.digital-human-button.is-connected:hover {
  background: var(--color-danger-soft);
  border-color: var(--color-danger);
  color: var(--color-danger);
  box-shadow: none;
}
.digital-human-status {
  margin: 0;
  text-align: center;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--color-text-muted);
  min-height: 17px;
}

/* ══ 卡片头部 ═══════════════════════════════════════════════════════ */
.chat-header,
.sidebar-header {
  padding: 18px 22px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

/* 品牌位：公司标（自定义 logo 或字母标）+ 公司名，值由 brand.json 下发 */
.header-brand {
  display: flex;
  align-items: center;
  gap: 7px;
}
.header-brand-mark {
  width: 20px;
  height: 20px;
  font-size: 10px;
}
/* 品牌位是运行时按 brand.json 注入的，节点不在模板里，scoped 选择器要用 :deep 穿透 */
.header-brand-mark :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}
.header-brand-name {
  font-size: 12.5px;
  color: var(--cp-ink2);
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  font-size: 19px;
  line-height: 1.3;
  letter-spacing: -0.01em;
  font-weight: 650;
  color: var(--color-text-primary);
}

.sidebar-header h2 {
  font-size: 17px;
}

.service-info {
  display: inline-flex;
  align-items: center;
  gap: 11px;
  padding: 7px 14px 7px 8px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  width: fit-content;
  max-width: 100%;
}

.service-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.service-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  background: var(--color-surface-3);
}

.status-indicator {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 11px;
  height: 11px;
  background: var(--color-success);
  border: 2px solid var(--color-surface);
  border-radius: 50%;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.service-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.service-status {
  font-size: 12px;
  color: var(--color-success);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
}
.service-status::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--color-success);
  border-radius: 50%;
}

.clear-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--duration-fast) linear;
}
.clear-button:hover {
  background: var(--color-danger-soft);
  border-color: var(--color-danger);
  color: var(--color-danger);
}
.clear-button svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

/* ══ sender_id 控制条 ═══════════════════════════════════════════════ */
.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
  padding: 14px 22px;
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface-2);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.field span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.field-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
  flex-wrap: nowrap;
  min-width: 0;
}

.field input,
.composer input {
  min-height: 42px;
  padding: 9px 13px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 14.5px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) linear, box-shadow var(--duration-fast) linear;
}

.field-row input {
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
}
.field-row .secondary-button {
  flex: 0 0 auto;
  white-space: nowrap;
}

.field input::placeholder,
.composer input::placeholder {
  color: var(--color-text-muted);
}
.field input:focus,
.composer input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus);
}

/* ══ 消息区 ═════════════════════════════════════════════════════════ */
.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--color-surface-2);
}

.turn-card {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--duration-base) linear, box-shadow var(--duration-base) linear;
  animation: msgEnter 0.34s var(--ease-out-expo) both;
}
@keyframes msgEnter {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.turn-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-sm);
}

.turn-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border-light);
}

.turn-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  background: var(--color-surface-3);
  color: var(--color-text-secondary);
  font-size: 11.5px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  font-variant-numeric: tabular-nums;
}

.turn-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 13px;
  font-weight: 600;
}

.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  display: block;
  border: 1px solid var(--color-border);
  background: var(--color-surface-3);
}

.user-avatar .avatar {
  border-color: var(--color-border-strong);
}
.service-avatar .avatar {
  border-color: rgba(16, 185, 129, 0.35);
}

.status-dot {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 10px;
  height: 10px;
  background: var(--color-success);
  border: 2px solid var(--color-surface);
  border-radius: 50%;
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.agent-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-label {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.user-section {
  align-items: flex-end;
}
.user-section .section-header {
  flex-direction: row-reverse;
}
.user-section .agent-info {
  align-items: flex-end;
}

.turn-bubble {
  padding: 11px 15px;
  border-radius: var(--radius-md);
  max-width: 100%;
  font-size: 14.5px;
}

/* 用户气泡：蓝色半透明底 */
.user-bubble {
  background: var(--color-accent-tint);
  border: 1px solid rgba(51, 112, 255, 0.20);
  color: var(--color-text-primary);
  margin-left: auto;
  max-width: 82%;
  border-bottom-right-radius: 4px;
}

/* 客服气泡：深色底描边 */
.bot-bubble {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
  border-bottom-left-radius: 4px;
  max-width: 92%;
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.turn-bubble p {
  margin: 0;
  font-size: 14.5px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: var(--color-text-primary);
}

/* 历史消息分隔线 */
.history-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-muted);
  font-size: 12.5px;
  padding: 4px 0;
}
.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border);
}
.history-divider span {
  padding: 5px 12px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 12px;
}

/* ══ 欢迎页 ═════════════════════════════════════════════════════════ */
.welcome {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.welcome-card {
  position: relative;
  max-width: 460px;
  width: 100%;
  padding: 38px 34px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  text-align: center;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  animation: msgEnter 0.4s var(--ease-out-expo) both;
}
.welcome-glow {
  position: absolute;
  top: -140px;
  left: 50%;
  transform: translateX(-50%);
  width: 340px;
  height: 260px;
  background: radial-gradient(circle, rgba(51, 112, 255, 0.10) 0%, transparent 70%);
  pointer-events: none;
}
.welcome-avatar-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 16px;
}
.welcome-avatar {
  width: 76px;
  height: 76px;
  border-radius: 50%;
  display: block;
  object-fit: cover;
  background: var(--color-surface-3);
  border: 2px solid var(--color-surface);
  box-shadow: var(--shadow-sm), 0 0 0 1px var(--color-border);
}
.welcome-status-pulse {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 15px;
  height: 15px;
  background: var(--color-success);
  border: 2.5px solid var(--color-surface);
  border-radius: 50%;
  animation: pulse 2.2s ease-in-out infinite;
}
.welcome-greeting {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
}
.welcome-subtitle {
  margin: 0 0 22px;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-bottom: 22px;
}
.welcome-chip {
  padding: 8px 16px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) linear;
}
.welcome-chip:hover:not(:disabled) {
  background: var(--color-accent-soft-bg);
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.welcome-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.welcome-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  justify-content: center;
  margin: 0;
  padding-top: 18px;
  border-top: 1px solid var(--color-border-light);
  color: var(--color-text-muted);
  font-size: 12.5px;
}
.welcome-features span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.welcome-features svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.75;
}

/* ══ 「正在输入」 ═══════════════════════════════════════════════════ */
.typing-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 9px;
  padding: 0 22px 12px;
  background: var(--color-surface-2);
  animation: msgEnter 0.28s var(--ease-out-expo);
}
.avatar-small {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid var(--color-border);
  background: var(--color-surface-3);
}
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  border-bottom-left-radius: 4px;
  box-shadow: var(--shadow-xs);
}
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.35; }
  30% { transform: translateY(-4px); opacity: 1; }
}
.typing-label {
  font-size: 12.5px;
  color: var(--color-text-muted);
}

/* ══ 对象卡片（订单 / 商品） ═══════════════════════════════════════ */
.object-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  min-width: 210px;
}
.object-card-order {
  border-color: rgba(51, 112, 255, 0.25);
  background: linear-gradient(180deg, rgba(51, 112, 255, 0.06), transparent 42%);
}
.object-card-product {
  border-color: rgba(245, 158, 11, 0.25);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.06), transparent 42%);
}
.user-bubble .object-card {
  background: var(--color-surface);
}
.object-card-badge {
  align-self: flex-start;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  background: var(--color-surface-3);
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.user-bubble .object-card-badge {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}
.object-card-title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--color-text-primary);
  word-break: break-word;
}
.object-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  word-break: break-all;
}
.object-card-price {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-warm);
  font-variant-numeric: tabular-nums;
}
.object-card-image {
  width: 100%;
  height: 112px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  border: 1px solid var(--color-border-light);
  background: var(--color-surface-3);
}
.turn-bubble .object-card {
  min-width: 210px;
}

/* ── 状态徽章 ────────────────────────────────────────────────────── */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: var(--radius-full);
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.status-warning {
  background: var(--color-warm-soft);
  color: var(--color-warm);
}
.status-info {
  background: var(--color-info-soft);
  color: var(--color-info);
}
.status-success {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.status-muted {
  background: var(--color-surface-3);
  color: var(--color-text-muted);
}
.status-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

/* ══ 通用按钮 ═══════════════════════════════════════════════════════ */
.secondary-button,
.tab-button,
.composer button {
  min-height: 42px;
  padding: 9px 16px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  line-height: 1.2;
  transition: background var(--duration-fast) linear, border-color var(--duration-fast) linear,
    color var(--duration-fast) linear, box-shadow var(--duration-fast) linear;
}
.secondary-button:hover:not(:disabled),
.tab-button:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: var(--color-accent-soft-bg);
}
.secondary-button:disabled,
.composer button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* ══ 底部输入区 ═════════════════════════════════════════════════════ */
.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 10px;
  padding: 14px 22px 16px;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-surface);
}
.composer input {
  flex: 1 1 auto;
  min-width: 0;
}
.composer button {
  min-width: 88px;
  flex: 0 0 auto;
  background: var(--color-accent);
  border-color: transparent;
  color: #ffffff;
}
.composer button:hover:not(:disabled) {
  background: var(--color-accent-strong);
  box-shadow: 0 6px 16px var(--color-accent-glow);
}

/* ══ 右侧业务对象侧栏 ═══════════════════════════════════════════════ */
.tabs {
  display: flex;
  gap: 4px;
  margin: 0 18px;
  padding: 3px;
  border-radius: var(--radius-md);
  background: var(--color-surface-3);
  margin-top: 14px;
  margin-bottom: 2px;
}
.tab-button {
  flex: 1;
  min-height: 34px;
  padding: 6px 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.tab-button.active {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-accent);
  box-shadow: var(--shadow-xs);
}
.tab-button.active:hover:not(:disabled) {
  background: var(--color-surface);
  border-color: var(--color-border);
  color: var(--color-accent);
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--color-surface-2);
}

.sidebar-card {
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  column-gap: 10px;
  row-gap: 4px;
  align-items: start;
  transition: border-color var(--duration-base) linear, box-shadow var(--duration-base) linear;
}
.sidebar-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-sm);
}

.card-image-wrapper {
  grid-column: 1;
  grid-row: 1 / span 3;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-3);
  border: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.sidebar-card:hover .card-image {
  transform: scale(1.03);
  transition: transform var(--duration-base) var(--ease-out-expo);
}
.card-image-placeholder {
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image-placeholder svg {
  width: 22px;
  height: 22px;
  opacity: 0.5;
}

.card-top {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 2px 8px;
  justify-content: space-between;
  align-items: flex-start;
  min-width: 0;
}
.card-title {
  flex: 1 1 5em;
  min-width: 0;
  font-size: 13.5px;
  line-height: 1.45;
  color: var(--color-text-primary);
  font-weight: 600;
}
.card-amount {
  flex-shrink: 0;
  color: var(--color-warm);
  font-weight: 700;
  font-size: 13.5px;
  font-variant-numeric: tabular-nums;
}
.card-meta {
  grid-column: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-secondary);
}
.sidebar-card > .secondary-button {
  grid-column: 1 / -1;
  margin-top: 4px;
}

.full-width {
  width: 100%;
}
.sidebar .secondary-button.full-width {
  min-height: 38px;
}

.sidebar-empty {
  margin: auto;
  max-width: 320px;
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
  line-height: 1.7;
}

/* ══ 气泡内的操作按钮（朗读 / 复制） ════════════════════════════════ */
.bot-text-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.bot-text-row p {
  flex: 1;
  margin: 0;
}
.bot-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  align-items: center;
}
.tts-button,
.copy-button {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  cursor: pointer;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) linear;
}
.tts-button svg,
.copy-button svg {
  width: 15px;
  height: 15px;
}
.tts-button:hover:not(:disabled),
.copy-button:hover:not(:disabled) {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}
.tts-button:disabled,
.copy-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.tts-button.tts-playing {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}
.tts-bars {
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 14px;
}
.tts-bars span {
  width: 3px;
  background: var(--color-accent);
  border-radius: 2px;
  animation: barBounce 0.6s ease-in-out infinite;
}
.tts-bars span:nth-child(1) { height: 7px; animation-delay: 0s; }
.tts-bars span:nth-child(2) { height: 13px; animation-delay: 0.15s; }
.tts-bars span:nth-child(3) { height: 9px; animation-delay: 0.3s; }
@keyframes barBounce {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}
.tts-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid var(--color-accent-soft);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: tts-spin 0.6s linear infinite;
}
@keyframes tts-spin {
  to { transform: rotate(360deg); }
}
.copy-button.copy-done {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.copy-button svg {
  display: block;
}

/* ══ 建议追问小胶囊 ═════════════════════════════════════════════════ */
.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid var(--color-border-light);
  width: 100%;
}
.suggestion-chip {
  padding: 5px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast) linear;
}
.suggestion-chip:hover:not(:disabled) {
  border-color: var(--color-accent);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
}
.suggestion-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ══ 错误提示 ═══════════════════════════════════════════════════════ */
.error-message,
.sidebar-error {
  margin: 0 22px 10px;
  padding: 9px 13px;
  border-radius: var(--radius-sm);
  background: var(--color-danger-soft);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--color-danger);
  font-size: 12.5px;
  font-weight: 500;
}
.sidebar-error {
  margin: 12px 18px 0;
}

/* ══ 滚动条：深色主题细条 ══════════════════════════════════════════════ */
.messages::-webkit-scrollbar,
.sidebar-list::-webkit-scrollbar,
.digital-human-body::-webkit-scrollbar {
  width: 8px;
}
.messages::-webkit-scrollbar-thumb,
.sidebar-list::-webkit-scrollbar-thumb,
.digital-human-body::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: var(--radius-full);
}
.messages::-webkit-scrollbar-thumb:hover,
.sidebar-list::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-strong);
}
.messages::-webkit-scrollbar-track,
.sidebar-list::-webkit-scrollbar-track {
  background: transparent;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(1.1); }
}

/* ══ 响应式 ═════════════════════════════════════════════════════════ */
/* 三卡横向是这一页的主形态。挂进统一外壳后 iframe 视口 = 浏览器宽度 − 240px
   侧栏，原先 1280px 的堆叠断点会在常见缩放档（125% / 150%）被误命中，页面塌成
   上下排列。这里把列宽改为 clamp 自适应，堆叠只在真放不下时（<900px）发生。 */
@media (max-width: 1600px) {
  .workspace {
    gap: 16px;
  }
}

@media (min-width: 901px) {
  /* 挂进外壳时（iframe 视口已扣掉 240px 侧栏）两侧卡片要给够宽度：
     数字人竖版舞台、以及业务对象里的订单标题+价格都不该被挤到换行。
     聊天区是中间弹性列，自然被压窄。 */
  html[data-cp-embedded="1"] .workspace {
    grid-template-columns: clamp(280px, 24vw, 420px) minmax(0, 1fr) clamp(288px, 25vw, 430px);
  }
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .chat-card { order: 1; }
  .digital-human-card { order: 2; }
  .sidebar { order: 3; }

  .sidebar,
  .digital-human-card {
    min-height: auto;
    height: auto;
  }

  .digital-human-body {
    padding-bottom: 16px;
  }

  .digital-human-stage-wrap {
    width: fit-content;
    max-width: 100%;
    margin: 0 auto;
  }
  .digital-human-stage {
    width: auto;
    height: min(42vh, 360px);
  }

  .messages {
    min-height: 320px;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
  }

  .chat-card,
  .sidebar,
  .digital-human-card {
    min-height: auto;
    height: auto;
    border-radius: 0;
    border-left: none;
    border-right: none;
    box-shadow: none;
  }

  .chat-card {
    min-height: 100vh;
  }

  .digital-human-stage-wrap {
    max-width: 240px;
  }

  .composer,
  .field-row {
    flex-direction: column;
    align-items: stretch;
  }

  .user-bubble,
  .bot-bubble {
    max-width: 100%;
  }
}

/* ══ 商务精装增量（深色主题下统一蓝色强调） ══════════════════════ */
.export-button:hover {
  background: var(--color-accent-soft-bg);
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.turn-header {
  justify-content: flex-start;
}
.turn-badge {
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
}

/* ══ [增量] 商务风皮肤覆盖（深色主题下仅微调，不再重定义整套令牌） ══ */
:global(body.biz-skin) {
  /* 深色主题下 biz-skin 仅强化顶部品牌色条 */
}

/* 顶栏：加一条蓝色品牌色条 */
:global(body.biz-skin) .chat-header {
  position: relative;
}
:global(body.biz-skin) .chat-header::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 3px;
  background: linear-gradient(90deg, #1a3a7a, #3370FF 55%, #60a5fa);
}
:global(body.biz-skin) .send-button,
:global(body.biz-skin) .chat-input-submit {
  border-radius: 10px;
  background: var(--color-accent);
}
:global(body.biz-skin) .chat-card,
:global(body.biz-skin) .sidebar,
:global(body.biz-skin) .digital-human-card {
  border-radius: 14px;
}

/* 皮肤切换按钮（固定右上角） */
.skin-toggle {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12.5px;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-fast) ease;
}
.skin-toggle:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
</style>

import { createApp } from 'vue'
import App from './App.vue'

// 统一设计令牌：作为 CSS 模块从共享目录直接注入（构建期读取磁盘并内联）。
// 用 `import` 而非 CSS `@import`，因为跨项目根的 @import 会被打包器静默丢弃。
import '../../../../../shared/ui-kit/tokens.css'
// 品牌桥：公司名与 logo 的唯一真源是 shared/config/brand.json（在外壳 ⚙ 里改）。
// 外壳网关端口构建期从 SERVICE_REGISTRY 取，不在代码里写死数字。
import registry from '../../../../../shared/config/services.json'
import { initBrandBridge } from '../../../../../shared/ui-kit/brand-bridge.js'

// ── 统一平台运行时桥（与 shared/ui-kit/ui-kit.js 契约一致）─────────────
// 深色为平台默认主题；作为 iframe 挂载到 shell 时接收 cp:theme / cp:auth，回传 cp:ready。
const THEME_KEY = 'cp_theme_v2'
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light')
  try { localStorage.setItem(THEME_KEY, t === 'dark' ? 'dark' : 'light') } catch (e) {}
}
function initCpBridge(moduleId) {
  let stored = 'light'
  try { stored = localStorage.getItem(THEME_KEY) || 'light' } catch (e) {}
  applyTheme(stored)
  let inIframe = true
  try { inIframe = window.self !== window.top } catch (e) { inIframe = true }
  if (!inIframe) return
  document.documentElement.setAttribute('data-cp-embedded', '1')
  window.addEventListener('message', (ev) => {
    const d = ev.data || {}
    if (d.source !== 'cp-shell') return
    if (d.type === 'cp:theme') applyTheme(d.theme)
    if (d.type === 'cp:auth') { try { sessionStorage.setItem('cp_token', d.token || '') } catch (e) {} }
  })
  try { window.parent.postMessage({ source: 'cp-module', type: 'cp:ready', module: moduleId, title: document.title }, '*') } catch (e) {}
}
initCpBridge('p01')
initBrandBridge({ registry })

createApp(App).mount('#app')

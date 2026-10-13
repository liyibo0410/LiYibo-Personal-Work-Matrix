import { createApp } from 'vue'
// 统一设计令牌：作为 CSS 模块从共享目录直接注入（构建期读取磁盘文件并内联）。
// 之所以用 `import` 而非 style.css 里的 `@import`：rolldown-vite 会静默丢弃跨项目根的
// CSS @import，令牌就不会进包；而显式的 CSS 模块 import 能被正确解析并打包。
import '../../../../shared/ui-kit/tokens.css'
import './style.css'
import App from './App.vue'
// 品牌桥：公司名与 logo 的唯一真源是 shared/config/brand.json（在外壳 ⚙ 里改）。
// 外壳网关端口构建期从 SERVICE_REGISTRY 取，不在代码里写死数字。
import registry from '../../../../shared/config/services.json'
import { initBrandBridge } from '../../../../shared/ui-kit/brand-bridge.js'

// ── 统一平台运行时桥（与 shared/ui-kit/ui-kit.js 契约一致）─────────────
// 深色为平台默认主题；本模块作为 iframe 挂载到 shell 时，接收 shell 下发的
// cp:theme / cp:auth，回传 cp:ready。契约字段与静态模块共用同一套，确保全局统一。
const THEME_KEY = 'cp_theme_v2'
function applyTheme(t: string) {
  document.documentElement.setAttribute('data-theme', t === 'dark' ? 'dark' : 'light')
  try { localStorage.setItem(THEME_KEY, t === 'dark' ? 'dark' : 'light') } catch (e) {}
}
function initCpBridge(moduleId: string) {
  applyTheme((() => { try { return localStorage.getItem(THEME_KEY) || 'light' } catch (e) { return 'light' } })())
  const inIframe = (() => { try { return window.self !== window.top } catch (e) { return true } })()
  if (!inIframe) return
  document.documentElement.setAttribute('data-cp-embedded', '1')
  window.addEventListener('message', (ev) => {
    const d: any = ev.data || {}
    if (d.source !== 'cp-shell') return
    if (d.type === 'cp:theme') applyTheme(d.theme)
    if (d.type === 'cp:auth') { try { sessionStorage.setItem('cp_token', d.token || '') } catch (e) {} }
  })
  try { window.parent.postMessage({ source: 'cp-module', type: 'cp:ready', module: moduleId, title: document.title }, '*') } catch (e) {}
}
initCpBridge('p03')
initBrandBridge({ registry })

createApp(App).mount('#app')

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
// 前端固定监听 5173（与 SERVICE_REGISTRY 中 p03.web_port 对齐）；
// 业务接口 /api、实时通道 /ws、产物静态目录 /outputs 全部代理到本模块后端 8030。
// 模块自身后端端口属本地配置（跨模块调用才必须走 SERVICE_REGISTRY 解析）。
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8030', changeOrigin: true },
      '/outputs': { target: 'http://127.0.0.1:8030', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8030', ws: true, changeOrigin: true },
    },
  },
})

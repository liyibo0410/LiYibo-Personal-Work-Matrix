import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next 16 的 dev server 默认只放行 localhost 来源的 /_next/* 请求；
  // 统一平台按 SERVICE_REGISTRY 用 http://127.0.0.1:3001 挂载本模块，
  // 浏览器带 Origin: http://127.0.0.1:3001 取 JS chunk 会被判为跨站并返回
  // 403，页面只剩服务端 HTML —— React 不水合，ECharts 画布一张都不出。
  allowedDevOrigins: ["127.0.0.1"],
};

export default nextConfig;

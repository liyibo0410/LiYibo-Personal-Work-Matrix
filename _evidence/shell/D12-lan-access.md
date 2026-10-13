# D12 · 局域网（同 WiFi）访问改造 —— 8800 在线系统对外可访问

日期：2026-10-13 · 环境：本机 WLAN `192.168.1.100` / SSID `512_5G`（Windows 判定为 Public 网络）
目标：让同一 WiFi 下的手机/他人能打开**真实在线系统** `http://192.168.1.100:8800/`，而不是静态截图。

## 根因

外壳 `shell/index.html` 与 `shared/ui-kit/ui-kit.js` 把模块地址拼成
`"http://" + REG.host + ":" + port`，而 `REG.host` 来自 `shared/config/services.json`
里写死的 `"host": "127.0.0.1"`。改绑定只解决「端口通不通」，不解决
「访客浏览器里的 127.0.0.1 指向谁」——访客的 127.0.0.1 是访客自己的机器，iframe 必然全白。

## 改动（7 处绑定 + 2 处前端主机）

| 文件 | 改动 |
|---|---|
| `shell/index.html:246` | 新增 `webHost()` → `location.hostname`，`webUrl()` 与离线横幅改用 `webHost()` |
| `shared/ui-kit/ui-kit.js:170` | `CP.serviceUrl()` 的 host 改为 `global.location.hostname` 优先，回退 `reg.host` |
| `shell/serve.py:45` | `DEFAULT_HOST` → `0.0.0.0`（`CP_SHELL_HOST` 仍可覆盖回环） |
| `_tools/supervisor.py:106` | P04 uvicorn `--host` → `0.0.0.0` |
| `projects/p01-.../customer-service-frontend/vite.config.js` | `server.host` → `0.0.0.0` |
| `projects/p03-deep-research/ui/vite.config.ts` | `server.host` → `0.0.0.0` |
| `projects/p05-contract-review/config/app.json` | `server.host` → `0.0.0.0` |
| `projects/p07-ai-asset-center/app/main.py:347` | `uvicorn.run(host=)` → `0.0.0.0` |
| `projects/p10-model-finetune/app/main.py:739` | `uvicorn.run(host=)` → `0.0.0.0` |

**有意不改**：P01 `api_port 18082`、P01 `commerce_port 18081`、P02 `api_port 8000` 保持回环。
依据：这三个端口只被服务端访问——P01/P03 前端经 vite `proxy` 转发（同源），
P02 的取数全部在 Next.js 服务端（`src/app/**/route.ts` 与 server component，实测引用
`@/lib/api` 的 12 个文件均非 `"use client"`），浏览器只跟 `:3001` 说话。
因此 **CORS 无需放宽**，本次未新增任何跨源放行。

## 验证

### 1. 绑定审计（`_tools/port_audit.py`，比对 services.json 与 netstat 实际监听）

改造前：`UP-ALL 8 / UP-LOOP 12 / DOWN 1`
改造后：`UP-ALL 18 / UP-LOOP 3 / DOWN 0`，剩余 3 个回环正是上面有意保留的 API 端口。

### 2. 逐个以局域网 IP 探测（非 127.0.0.1）

```
shell  :8800  => 200      p06  :8060 => 200
p01-web:5173  => 200      p07  :8070 => 200
p02-web:3001  => 307      p08  :8080 => 200
p03-web:5174  => 200      p09  :8090 => 200
p04   :8041  => 307      p10  :8101 => 200
p05   :8770  => 302      （307/302 为登录跳转，非失败）
```

### 3. 浏览器真实走通（以 `http://192.168.1.100:8800/` 打开，非本机回环）

- 登录：点 `owner` 演示 chip → `POST /api/auth/login` **200**，`user-badge = 张总 owner`
- 服务探活：`GET /api/services/health` → 10 个模块 `online:true`，端口全 true
- 挂载 P06：`iframe.src = http://192.168.1.100:8060/?cp-theme=dark`，
  文档 **200**，且模块自身取数 `GET http://192.168.1.100:8060/api/v1/dashboard` **200**、
  `GET http://192.168.1.100:8060/shared/config/brand.json` **200** —— 证明访客浏览器里的
  局域网主机确实解析到了本机服务，离线横幅 `display:none`
- 挂载 P02：`iframe.src = http://192.168.1.100:3001/?cp-theme=dark` → 跳
  `http://192.168.1.100:3001/login` **200**（P02 保留自身 Cookie RBAC，见 ADR-0003）
- 控制台：仅 2 条既有告警（iframe `sandbox` 同时含 allow-scripts 与 allow-same-origin），
  **无 CSP / CORS / 连接失败类报错**

## 诚实边界

1. **无截图**。browser-use 的 `take_screenshot` 报
   `NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`（in-app browser 面 `visibilityState=hidden`），
   Edge 无头又无法带登录态进入 iframe 挂载页。故本节证据为**网络层与 DOM 层的实测数据**
   （请求 URL + 状态码 + `iframe.src` + 健康接口返回），不是截图。
2. **P02 需二次登录**。外壳令牌不会自动登入 P02（有意例外），访客要用
   `boss@cloudpivot.com / Test123456` 再登一次。
3. **`health` 接口仍返回 `"host": "127.0.0.1"`**（`services.json` 未动）。前端已不再消费该
   字段拼 URL，故不影响；保留它是因为服务端探活确实该连本机回环。
4. **暴露面**。10 个服务现在监听 `0.0.0.0`，且 WLAN 是 Public 配置文件，同 WiFi 下任意
   设备可访问。要收回：把上述 7 处改回 `127.0.0.1` 并 `python _tools/supervisor.py restart`。
5. **依赖本机 IP**。`192.168.1.100` 是 DHCP 所得，重连路由器后可能变化，届时链接需更新
   （iframe 主机跟随 `location.hostname`，所以只要用新 IP 打开外壳，内部链接自动跟着变）。

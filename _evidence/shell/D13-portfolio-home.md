# D13 · 工作台首页改为作品集首页（含远程访问链路实测）

日期：2026-10-13 · 改动文件：`shell/index.html`、`shell/serve.py`、新增 `_tools/tunnel.py`

## 一、做了什么

| 项 | 改动 |
|---|---|
| 首页形态 | `#home-view` 从「AI 智能体矩阵」（hero + 统计 + 闭环图 + 简版卡）改为**完整作品集首页**：访客顶栏 → hero → 统计条 → 十大模块卡（按四层） → 数据流闭环 + 6 条 ADR → 可复核的评测（6 张证据卡 + P04 Ragas 对照表） → 真实/模拟边界（10 条） → 关于作者与阅读路线 → 页脚 |
| 登录门禁 | 整屏登录页 `#login-view` 删除，改为**登录模态** `#login-modal`；未登录可读完整个首页，点「进入演示」才拦（`router()` 里做门禁，登录后回跳原目标路由） |
| 侧栏 | 导航项「工作台首页」→「作品集首页」；顶栏标题同步 |
| 卡片信息量 | 每张模块卡带：技术栈、**实测指标**（通过数/召回率/自检数）、**Mock 边界黄框**、真实 TCP 探活标签、`route:port` |
| 公网地址支持 | `webUrl()` 增加 `public_url` 分支：本机/局域网访客继续 `location.hostname:port`（同站点，Cookie 不被拦），只有页面自身从公网域名打开时才用隧道地址 |
| 网关下发 | `/api/services/health` 响应新增 `public_urls`（读 `_runtime/tunnel/public_urls.json`，无文件返回 `{}`），前端每 6s 随探活合并，隧道域名轮换不需要重新生成 `services.js` |
| 安全加固 | 静态服务改**扩展名白名单**：此前 `GET /serve.py` 会把网关源码（含 `DEMO_ACCOUNTS` 明文口令）整份下载走。现只发 html/js/css/json/图片/字体，其余 403 |

数据来源：所有指标取自 `README.md` 第五节与 `_evidence/` 实测记录，未新增任何未测数字。

## 二、实测记录

### 1. 访客态（无令牌）

`_tools/shot.py` 无头 Edge 真实渲染 + DOM 探针：

```
public=true | cards=10 | mocks=10 | nav=flex | modal=none
statbar: 10 AI 能力模块 ; 4 架构分层 ; 506 pytest 实跑通过 ; 6 技术选型 ADR ; 9/10 服务探活
tags:    运行中 ×9, 未启动 ×1（P07 素材中心当时确实没起）
```

截图：`portfolio-home-guest.png`（1440×1500）、`portfolio-home-guest-full.png`（整页）、
`portfolio-home-mobile.png`（390×1400，`navLinks=none`、无横向滚动）。

### 2. 门禁与回跳

浏览器真实点击链（browser-use，非模拟返回值）：

| 步骤 | 结果 |
|---|---|
| 点 P01 卡「进入演示」 | `hash=#/workspace/customer-service`、`modal=flex`、首页仍可见（`homeVisible=true`）、提示语「『AI 电商客服』是本机在跑的真实系统…」 |
| 点「先随便看看」 | `modal=none`、`hash` 已被 `history.replaceState` 清回 `#/` |
| **再次**点同一张卡 | `modal=flex`（修 hash 残留前的回归点：不清 hash 则第二次点击不再触发 `hashchange`，弹窗再也不出来） |
| 填充 `owner` 并提交 | `token=true`、`modal=none`、`public=false`、自动挂载 `iframe src=http://127.0.0.1:5173?cp-theme=light`、顶栏「AI 电商客服」、无离线横幅 |
| 登录后 hero 主按钮 | 文案切为「进入在线演示 · 旗舰 P02」，`data-open-login` 属性移除；点击 → `#/workspace/ecommerce-ops` → `iframe src=http://127.0.0.1:3001` |

截图：`portfolio-login-gate.png`（弹窗态）、`portfolio-home-authenticated.png`（登录态 + 侧栏）。

### 3. 网关与封堵

```
GET  /                       200  (56321 B)
GET  /api/services/health    {"public_urls": {}, "online": 9/10}
GET  /serve.py               403   ← 加固后（加固前可整份下载源码与演示口令）
GET  /shared/ui-kit/tokens.css   200
GET  /shared/config/brand.json   200
```

### 4. 过程中修掉的两个真缺陷

1. **首页整页白屏、控制台无报错**：`btn-theme-public` 漏登记进 `els` 的 id 清单 →
   顶层 `TypeError` 让整段 IIFE 在 `boot()` 之前中断。定位方式：把内联脚本取出来
   `node --check`（语法 OK）→ 在页面里 `eval` 才逼出异常栈。
2. **关掉弹窗后二次点击不再弹**：门禁分支留着 `#/workspace/xxx` 的 hash 没清，
   同值赋值不触发 `hashchange`。已用 `history.replaceState` 清回 `#/`。

## 三、远程访问链路：**被本机 VPN 阻断，未打通**

选定路线是 cloudflared 快速隧道。工具已写好（`_tools/tunnel.py start/stop/status`，
按 SERVICE_REGISTRY 给网关与各模块 web 端口分别开隧道，写 `_runtime/tunnel/public_urls.json`，
**自校验 `/api/health` 通过才对外发链接**，不通过就不落盘）。

但隧道在本机建不起来，根因不是配置：

```
precheck  UDP  Connectivity  region1/2.v2.argotunnel.com  FAIL  QUIC connection failed
precheck  TCP  Connectivity  region1/2.v2.argotunnel.com  FAIL  HTTP/2 connection is blocked or unreachable
运行期    ERR  Serve tunnel error  error="TLS handshake with edge error: EOF"   ip=198.18.0.245
访客侧    curl https://<随机>.trycloudflare.com/api/health → HTTP 530 (Cloudflare error 1033)
```

- `ipconfig` 显示存在名为 **「快车VPN」** 的 TUN 网卡，地址段 `198.18.0.1`，且 DNS 返回
  `198.18.0.245/246` 这类 **fake-IP** —— 说明全部出站流量（含 cloudflared 直连）都被它接管并做 TLS 中间人。
- 系统代理 `127.0.0.1:7890` 同样不通：`curl -x http://127.0.0.1:7890 https://region1.v2.argotunnel.com`
  → `schannel: SEC_E_ILLEGAL_MESSAGE`（握手被伪造/掐断）。
- 对照实验：同一网络下到 GitHub Releases 的 HTTPS 正常（cloudflared 二进制 52.8 MB 已下载成功），
  所以不是断网，是**这条隧道协议过不去**。

因此 `_tools/tunnel.py` 目前的真实输出是诚实失败：

```
链接不可用： https://flow-inclusion-communication-applied.trycloudflare.com → URLError: SSL UNEXPECTED_EOF_WHILE_READING
域名已分配但取不到内容 …… 给 argotunnel.com / trycloudflare.com 加 DIRECT 且跳过 TLS 中间人，或演示时暂停 TUN。
```

### 待使用者定的三条出路

| 方案 | 需要谁动手 | 代价 |
|---|---|---|
| A. 在「快车VPN」里给 `argotunnel.com` / `trycloudflare.com` 加 DIRECT 且**不做 TLS 中间人**（或演示时暂停 TUN） | 使用者改本机代理配置（AI 不动系统级设置） | 之后 `python _tools\tunnel.py start` 一条命令出链接；域名每次重启会变 |
| B. 走阿里云 `39.96.200.45`：SSH 反向隧道 + nginx 多端口 | 使用者给 SSH 授权 + 安全组开端口 | 已实测该机 22 端口 TCP 可达、`known_hosts` 有历史条目；SSH 不是 TLS，代理中间人拦不住；同主机不同端口=**同站点**，iframe 里 P02 的 Cookie 不会被当第三方 Cookie 拦掉（比 trycloudflare 多域名更干净）。代价是服务器内存偏小、8000 端口已被产品管理台占用需避开 |
| C. 只发静态作品集站（Qoder Sites 已有 `cloudpivot-portfolio-*.qoder.zone`） | 无需改动 | 链接稳定、手机可看、零暴露风险，但面试官点进去是看图不能操作 |

## 四、诚实边界

- **远程链接尚未交付**：本机 VPN 阻断，未做任何「假装能访问」的处理。
- 自校验是从本机发出的，同一台机器上的 VPN 也会中间人 `trycloudflare.com`，
  所以存在「本机探测失败但外部访客其实可用」的理论可能 —— 方案 A 落地后需用手机蜂窝网络或
  外部站点二次确认，不能只信这条自校验。
- 首页数字全部沿用 README 实测值；`服务探活` 是实时 TCP 探测结果，截图时为 9/10（P07 未起），
  复测时 10/10 —— 这个数会随进程状态浮动，不是写死的。
- 未做：并发压测、覆盖率（沿用 README 第九节声明）。
- `01-portfolio/index.html`（静态门户）本轮**没动** —— 另一个并行会话正在改它，避免互相覆盖；
  两份作品集内容因此存在口径差异，待该会话收尾后统一。

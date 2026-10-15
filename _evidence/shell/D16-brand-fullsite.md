# D16 · 品牌定制全站打通（2026-10-13 晚）

> 用户反馈：**「logo 还有名字还是不能自定义」**。
> 结论：外壳 8800 的读写链路本身是通的（实测改名 + 传 logo + 刷新持久化都生效），
> 真正坏的是**「全站生效」这一半** —— 十个入口里有六个根本拿不到 brand.json，
> 再加上一个跑着旧代码的网关进程占着 8801，在那个入口里改品牌必然全部失败。

## 根因（逐条实测，不是推测）

| # | 现象 | 根因 | 证据 |
|---|---|---|---|
| 1 | 某个入口里改名/传 logo 完全没反应 | **8801 上跑着 8:26 启动的旧 `shell/serve.py`**（品牌接口是 18:52 才加的），`GET/POST /api/brand` 一律 404；而它托管的 `index.html` 是磁盘上的新文件，所以⚙面板在、接口不在 | `curl :8801/api/brand` → `404 资源不存在`（杀进程前）；`taskkill /PID 5220` 后端口释放 |
| 2 | P04 问答页公司名/logo 永远默认 | `chat.html` **压根没引入 ui-kit.js / services.js**，`data-cp-brand` 是死绑定 | 修复前浏览器实测 `window.CP === undefined` |
| 3 | P04 控制台只有 logo 没有公司名 | 缺 `data-cp-brand-src` 声明与 company 节点 | 同上 |
| 4 | P05 合同系统不跟品牌走 | 7 个页面都挂了 ui-kit，但**整页零品牌节点**（公司名写死在 `app.js` 的 `BRAND` 常量里） | 修复前 `document.querySelectorAll('[data-cp-brand]').length === 0` |
| 5 | P01 / P03 不跟品牌走 | 运行时桥只处理 `cp:theme` / `cp:auth`，**没有 `cp:brand` 分支**；页面上也没有品牌位 | `src/main.js` / `src/main.ts` 的 `initCpBridge` |
| 6 | P02 旗舰不跟品牌走 | 无品牌桥；`layout.tsx` 把「电商运营助手 · 李奕波个人作品矩阵」写成 `metadata` 常量；Next 的 origin 上 `/shared/config/brand.json` 是 404 | 修复前 `fetch('/shared/config/brand.json')` → 404，DOM 里 2 处硬编码 |
| 7 | 门户 / 移动端画廊时好时坏 | 只声明了相对路径 `../shared/config/brand.json`，**没引 services.js**，所以既没有同源文件可读、也没有网关端口可兜底 | 修复前 8801 上打开门户：能取到 brand.json 却仍渲染默认值（旧网关无接口 + 无端口来源） |

## 做了什么

**单一真源与兜底通道**

- `shared/config/services.json` 新增顶层 `gateway.web_port = 8800`（**不进 `services` 表**，否则外壳会把它当成一个模块列进导航与探活清单）；`build_js.py` 同步导出，重生成 `services.js`
- `shell/serve.py`：`GET /api/brand` 加 `Access-Control-Allow-Origin: *`（brand.json 无密钥且本就作为 `/shared/*` 公开）；`POST` 仍要求登录令牌，未动
- `shared/ui-kit/ui-kit.js`：`CP.loadBrand` 从「只读一个同源地址」改成**来源链**：页面声明的同源 `brand.json` → 外壳网关 `GET /api/brand`（端口只从 `CP_REGISTRY.gateway` 解析，取不到就不猜）；`boot()` 改为无条件尝试，页面忘写 `data-cp-brand-src` 也能生效
- 新增 `[data-cp-brand-logo-src]` 绑定类型：**有自定义 logo 用它、没设就用页面自带标识**（给 P05 衡鉴、P02 这类有自己产品 mark 的模块用）；`applyBrand` 结束时派发 `cp:brand-applied` 事件，供 JS 渲染顶栏/页脚（P05）和框架托管 DOM 的代码重绘

**构建型模块**

- 新增 `shared/ui-kit/brand-bridge.js`（+ `.d.ts`）：P01 / P03 共用的 ES 模块品牌桥，契约与 `CP.applyBrand` 一致，含 `cp:brand` postMessage 监听、网关兜底拉取、以及 MutationObserver 补挂（框架重渲染后品牌自动补回；写入前比对，值一致不写所以不会自激）
- P01：`main.js` 接桥 + 页头加品牌位 + `index.html` 标题改 `{company}` 模板
- P03：`main.ts` 接桥 + 欢迎页品牌位 + 标题模板
- P02（Next.js）：新增 `app/api/brand/route.ts`（同源只读，`middleware.ts` 放行该路径）、`lib/brand.ts`（纯数据契约，RSC 可引）/`lib/brand-store.ts`（`useBrand()`，客户端）/`lib/brand-server.ts`（服务端读盘）、`components/cp-brand-bridge.tsx`；`layout.tsx` 的 `metadata` 改成 `generateMetadata`（**SSR 出的标题就带公司名**）；`app-shell.tsx` 侧栏与 `login/page.tsx` 换成品牌位（自定义 logo 优先，否则原图标）

**静态侧**

- P04：`chat.html` 补 tokens/services/ui-kit 三个引入 + company 品牌位；`console.html` 补 `data-cp-brand-src` + company 绑定
- P05：7 个页面统一声明 `data-cp-brand-src`；`app.js` 顶栏与版权页脚接品牌位并在注入后重放 `applyBrand`；登录页 logo 走 `data-cp-brand-logo-src`（主题切换时同步兜底图，避免把自定义 logo 刷回深色版）
- 门户 / 移动端画廊：补 `services.js` 引入（否则拿不到网关端口，兜底链断）；画廊 h1 加 logo 位

## 验证（13 个入口，临时改名为「启明科技 / Qiming Tech」后逐张出图）

脚本 `_tmp_issue/shot_brand_surfaces.py`（Edge headless + `--virtual-time-budget=12000`，跑完自动还原配置），产物在 `_evidence/shell/`：

| 截图 | 入口 | 结果 |
|---|---|---|
| `D16-brand-shell-8800.png` | 外壳 8800 | 跟随 |
| `D16-brand-p01-5173.png` | P01 客服 | 页头品牌位 + 自定义 logo |
| `D16-brand-p02-login-3001.png` | P02 旗舰登录 | 服务端渲染即带「启明科技」，登录卡显示自定义 logo |
| `D16-brand-p03-5174.png` | P03 问数 | 欢迎页品牌位跟随 |
| `D16-brand-p04-chat-8041.png` | P04 问答页 | 补引入后才真正生效 |
| `D16-brand-p05-login-8770.png` | P05 合同登录 | 公司名 + 自定义 logo 覆盖自带标识 |
| `D16-brand-p06-8060.png` … `p10-8101.png` | P06–P10 | 五张全部跟随 |
| `D16-brand-portfolio-file.png` | 门户（`file://` 双击打开） | 「启明科技 Qiming Tech」+ logo，走网关兜底 |
| `D16-brand-gallery-file.png` | 移动端画廊（`file://`） | 同上 |

**实时下发**（外壳保存 → 模块不刷新即变）：P01 / P02 / P03 / P06 各做了一次 `postMessage({source:'cp-shell',type:'cp:brand'})` 实测，DOM 与 `document.title` 即时更新；P02 在 logo 置空时正确回落到原 Sparkles 图标。

**持久化**：外壳改名换 logo → 刷新 → `document.title`、侧栏、登录页全部保留（`fetchBrand` 走 `/api/brand`）。

## 未闭环 / 遗留（不当成已完成）

- **外壳 iframe 内的实时下发只能靠代码路径证明**：模块与外壳不同源，父页读不到 iframe DOM，无法截图取证；已验证的是「模块侧监听可用」（顶层 postMessage）+「外壳保存后会广播」（`shell/index.html` 的 `renderBrand → broadcastBrand → pushToModule`）。
- P01 / P03 的网关端口是**构建期**从 `services.json` 注入的（与 tokens 内联同一策略，见 ADR-0005）：改了 `gateway.web_port` 要重启这两个 dev server 才生效。
- P02 的 `/api/brand` 直读磁盘：容器化部署若没把 `shared/` 挂进去会回落默认值（此时挂载进外壳仍能由 postMessage 拿到真实品牌）—— 已在代码注释写明。
- `shared/config/brand.json` **至今没进 git**（`git show HEAD:shared/config/brand.json` → not in HEAD）。它是全站品牌唯一真源，但里面存的是用户上传的 logo dataURL（当前 29 KB），要不要入库需用户定口径；现状是新克隆仓库时走各模块默认值、首次保存会自动创建。
- 8801 那个旧进程属手工启动残留，`supervisor` 不托管它；已按用户决定杀掉，只保留 8800 一个网关。
- 本轮改动均在工作区，**未 commit、未 push**。

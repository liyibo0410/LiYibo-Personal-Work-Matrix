# 截图墙建档 · 李奕波个人作品矩阵 Li Yibo's Personal Portfolio 作品集

> 建档人：证据与截图策展（D 号）｜建档时间：2026-10-15｜方法：**每张图都用 `read` 工具实际打开看过**（Pillow 12.3.0 实测宽高与字节数），不按文件名臆测画面。
> 本文只覆盖三个既有目录：`_evidence/screenshots/`、`_evidence/portfolio/`、`_evidence/portfolio-matrix/`。
> 所有路径均为**相对仓库根**的路径，可直接粘进根 `README.md`。`_evidence/` 下的任何文件**未做任何改动**（只读）。
> 本文未验证的地方一律显式标注「未验证」。

---

## 一、逐张建档

> 列含义：**主体**＝目视看到的画面内容（看不清写「无法辨认」）；**明/暗**＝浅色态 / 深色态；**隐私**＝手机号 / 邮箱 / 真实姓名的逐张核查结论；**用途**：首屏 / 模块墙 / 仅证据。

### A. `_evidence/screenshots/`（12 张 PNG + 1 个 zip）

| 路径 | 宽×高 | 大小 | 长宽比 | 画面主体（目视） | 明/暗 | 中文 | 隐私（手机号/邮箱/姓名） | 用途 | 建议图注 |
|---|---|---|---|---|---|---|---|---|---|
| `_evidence/screenshots/p01.png` | 1400×900 | 121.6 KB | 1.556 | 电商客服工作台三栏：左「数字人 · 听澜（未连接）」、中对话流（用户 `u1001` 聊退款/订单，客服「听澜 · 金牌客服」回复）、右「业务对象」面板；**右栏是错误态**——红字「加载订单列表失败。」+「暂无订单数据」 | 深色 | 是 | 无 | 模块墙（缩略）/ 仅证据 | P01 AI 电商客服：意图识别 → 知识检索 → 生成回复，对话态可中断/恢复 |
| `_evidence/screenshots/p02.png` | 1400×900 | 18.9 KB | 1.556 | P02 登录页「登录工作台 / Ecommerce Operation Assistant」，邮箱框、密码框、登录按钮、返回首页 | 深色 | 是 | **仅占位符** `owner@example.com`（示例邮箱，非真实） | 模块墙 / 首屏（登录流程） | P02 电商运营助手：登录工作台，四角色 RBAC |
| `_evidence/screenshots/p03.png` | 1400×900 | 33.0 KB | 1.556 | 英文欢迎页「Hello, User / How can I help you today?」+ 输入框 + 一行英文免责声明（DeepAgents 可能给出不准确信息）。画面较空 | 深色 | 主体英文 | 无 | 模块墙（缩略）/ 仅证据 | P03 NL2SQL 问数：自然语言 → SQL → 图表 |
| `_evidence/screenshots/p04.png` | 1400×900 | 29.3 KB | 1.556 | P04「BOSS智库 · 智能知识管理平台」文件导入页，侧栏 上传导入/文档管理/检索问答/数据看板，中央拖拽上传区（支持 PDF / Markdown） | 深色 | 是 | 无 | 模块墙 | P04 RAG 知识库：文档导入 → 解析入库 → 检索问答 |
| `_evidence/screenshots/p05.png` | 1400×900 | 294.2 KB | 1.556 | P05「衡鉴 V2.1.9 · 企业合同智能审查系统」登录页：左账号/口令表单，右三个「演示身份 · 一键进入」卡（法务审查人 legal / 业务经办人 applicant / 系统管理员 admin）。**页面底部署名处明文印出演示账号与初始口令 `legal / applicant / admin`，口令 `Legal@2026 / Apply@2026 / Admin@2026`** | 深色 | 是 | 无手机号/邮箱；**含明文演示口令（凭据泄露，见第三节）** | 仅证据 | P05 合同审批：三角色 RBAC（legal / applicant / admin） |
| `_evidence/screenshots/p06.png` | 1400×900 | 26.3 KB | 1.556 | P06 数据中台「数据总览」，侧栏六项；**三块卡片（数据健康度 / 数仓分层 / 核心指标概览）内容为空，标题旁「加载中…」**——截图停在加载态 | 深色 | 是 | 无 | 仅证据（画面为空态）/ 模块墙（缩略） | P06 数据中台：数据健康度 · 数仓分层 · 核心指标 |
| `_evidence/screenshots/p07.png` | 1400×900 | 40.6 KB | 1.556 | P07「AI 素材中心 · 素材概览」：KPI 卡 素材总数 12 / 已关联投放 7 / 总花费 ¥43,200 / 整体 ROI 10.38x；右上「Mock 模式」徽标；**两个图表（素材类型分布、投放 ROI 排行）无数据条** | 深色 | 是 | 无 | 模块墙 | P07 AI 素材中心：素材管理 · 智能打标 · 以文搜图 · 投放关联 |
| `_evidence/screenshots/p08.png` | 1400×900 | 81.5 KB | 1.556 | P08「直播切片 · 数据概览」：KPI 直播场次 3 / 生成切片 15 / 平均评分 68.4 / 任务队列 0；热门关键词表（下单·回购·小龙虾·限量·精华…）；最近切片列表。左下「v1.0.0 · Mock Mode」+「ASR / 评分 / 视频 均为模拟」 | 深色 | 是 | 无 | 模块墙 | P08 直播切片：ASR 转写 · 高光打分 · 自动切片（Mock 边界在画面内） |
| `_evidence/screenshots/p09.png` | 1400×900 | 60.5 KB | 1.556 | P09「Assessment Dashboard」（英文 UI，P09 Module 徽标）：顶部橙色 Mock 提示；KPI 23 / 5 / 80.7 / 15；Score Distribution 柱图为空，Dimension Averages 雷达图有 5 维 | 深色 | 主体英文 | 无 | 模块墙 | P09 AI 销售考核：会话质检 · 多维评分 · 排行榜 |
| `_evidence/screenshots/p10.png` | 1400×900 | 41.9 KB | 1.556 | P10「Dashboard」（英文 UI）：Mock Mode 橙色横幅（训练/评测/部署均为模拟）；KPI 3 / 2 / 3 / 45,700 / 83.7% / 1；Recent Training Runs 表两行（`cs-qa-lora-run1`、`product-desc-qlora-run2`，completed） | 深色 | 主体英文 | 无 | 模块墙 | P10 模型微调平台：数据集 · 训练 · 评测 · 模型仓库（Mock 模式） |
| `_evidence/screenshots/portfolio.png` | 1400×900 | 122.0 KB | 1.556 | **旧版**作品集首页（深色）：「李奕波个人作品矩阵 Li Yibo's Personal Portfolio」大标题 + 10 / 4 / 200+ / 50万 指标 + 「十大模块」标题起步。与 `live-before-20261014.png` 同代 | 深色 | 是 | 无 | 仅证据（旧版对照） | 改造前：旧版作品集首页 |
| `_evidence/screenshots/shell.png` | 1400×900 | 69.1 KB | 1.556 | **统一外壳工作台**：中「欢迎使用 李奕波个人作品矩阵」，左分层导航（L3 应用：P01/P02/P05/P09；L2 能力：P03/P04/P07/P08；模型&数据：P10/P06；门户：工作台首页），右十张模块入口卡（每卡有状态点）。右上角身份显示 **`张总（老板）` · Owner（演示角色名，非真实姓名）** | 深色 | 是 | 无 | **首屏候选** / 模块墙 | 统一外壳：一个入口挂载十个模块，左侧按四层架构导航 |
| `_evidence/screenshots/screenshots-mobile.zip` | — | 899.5 KB | — | 压缩包（非图片，未解包核对内容——**未验证**） | — | — | **未验证** | 仅证据（归档） | 移动端截图归档 |

### B. `_evidence/portfolio/`（4 张）

| 路径 | 宽×高 | 大小 | 长宽比 | 画面主体（目视） | 明/暗 | 中文 | 隐私（手机号/邮箱/姓名） | 用途 | 建议图注 |
|---|---|---|---|---|---|---|---|---|---|
| `_evidence/portfolio/static-site-top.png` | 1280×1300 | 201.7 KB | 0.985 | **新版静态作品集首屏（浅色）**：「一套能点开就跑的 AI 电商运营中台」+ 指标 10 / 4 / 556 / 6 / 36+36 + 前两行模块卡（P01/P02/P05，带真实界面缩略 + Mock 边界黄条）。顶部有一段明确写道「关于『在线演示』…未做公网部署——所以这里不放一个会 502 的假链接」 | **浅色** | 是 | 无（本视图不含姓名） | **首屏首选** | 一套能点开就跑的 AI 电商运营中台：十个模块 · 四层架构 · 真实或标注 |
| `_evidence/portfolio/portfolio-home.png` | 1280×2400 | 311.3 KB | 0.533 | 新版作品集首页（深色）：「用 AI 重构电商运营的每一个环节」+ 指标 10 / 4 / 36 / 180 + 旗舰卡 P02 + 十大能力模块卡（P01…P10，均标「已运行」）+ 数据闭环架构 | 深色 | 是 | 无（姓名在更下方的作者区，本视图未见） | 首屏候选（长图） | 首页作品集：四层模块卡 + 数据闭环 + ADR 索引 |
| `_evidence/portfolio/portfolio-full.png` | 1280×3400 | 397.1 KB | 0.376 | 新版作品集**整页长图**（深色）：模块卡 + 数据闭环 + 技术栈 + 关于作者。底部作者区署 **真实姓名「李奕波 · 2026 · 基于统一设计系统 shared/ui-kit 构建」** | 深色 | 是 | **含真实姓名「李奕波」**（作者本人署名） | 仅证据 / 首屏需裁剪掉作者区 | 作品集整页（含技术栈与作者信息） |
| `_evidence/portfolio/live-before-20261014.png` | 1280×1200 | 169.1 KB | 1.067 | **改造前旧版**首页（深色）：与 `screenshots/portfolio.png` 同款，P09/P08 标「**构建中**」；右下角有「Made with Qoder」水印 | 深色 | 是 | 无 | 仅证据（前后对比） | 改造前：旧版首页（P08/P09 仍在构建中） |

### C. `_evidence/portfolio-matrix/`（7 张，均含真实姓名，见第三节）

| 路径 | 宽×高 | 大小 | 长宽比 | 画面主体（目视） | 明/暗 | 中文 | 隐私（手机号/邮箱/姓名） | 用途 | 建议图注 |
|---|---|---|---|---|---|---|---|---|---|
| `_evidence/portfolio-matrix/self-check-desktop.png` | 1440×1100 | 114.1 KB | 1.309 | 矩阵式「作品矩阵」首屏：大字 hero **「李奕波 / LI YIBO」** + 「把十个 AI 能力模块，跑成同一套中台。」+ 指标 10 / 731 / 4 / 6 + 按钮「查看作品矩阵 / 在线演示（本机:8800）/ 材料 PDF」 | 深色 | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据（含姓名） | 作品矩阵首页（深色） |
| `_evidence/portfolio-matrix/self-check-light.png` | 1440×1100 | 116.7 KB | 1.309 | 与上同视图，浅色主题 | **浅色** | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据（含姓名） | 作品矩阵首页（浅色） |
| `_evidence/portfolio-matrix/self-check-dark.png` | 1440×1100 | 112.8 KB | 1.309 | 与 `self-check-desktop` 基本同一深色视图（主题切换的深色态留档） | 深色 | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据 | 作品矩阵首页（深色主题） |
| `_evidence/portfolio-matrix/self-check-mobile.png` | 390×880 | 48.5 KB | 0.443 | 移动端 390px 首屏（浅色）：姓名 + 主张 + 两个按钮 + 指标卡起始。响应式证据 | **浅色** | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据（响应式） | 移动端首屏（390px） |
| `_evidence/portfolio-matrix/self-check-full.png` | 1440×5600 | 598.1 KB | 0.257 | **整页长图（浅色）**：01 作品矩阵 / 02 口径（数据在模块间真实流动）/ 03 证据（每个数字可点开原始日志）/ 04 工程决策（六条 ADR）/ 05 真实边界（「没做完的，也放上来」） | **浅色** | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据 | 作品矩阵整页（含六条 ADR 与真实边界） |
| `_evidence/portfolio-matrix/theme-01.png` | 1440×1600 | 671.6 KB | 0.900 | 「作品矩阵」首屏 + 下方四张模块卡（P01 AI 电商客服 / P02 电商运营助手 / P05 合同审批·衡鉴 / P09 AI 销售考核），暖色（砖红）主题 | **浅色** | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据（主题样例） | 主题样例一（暖色） |
| `_evidence/portfolio-matrix/theme-02.png` | 1440×1600 | 199.5 KB | 0.900 | 同 `theme-01` 视图，暖色 + 网格背景主题 | **浅色** | 是 | **含真实姓名「李奕波 / LI YIBO」** | 仅证据（主题样例） | 主题样例二（暖色 + 网格） |

---

## 二、可复用性小结（结论，供挑图）

- **最适合进 README 首屏的 2 张**：`_evidence/portfolio/static-site-top.png`（浅色、自证「不放会 502 的假链接」、含 Mock 边界标注）与 `_evidence/screenshots/shell.png`（深色统一外壳，一个入口挂十模块）。两者一浅一深，覆盖「作品集主张」与「统一架构」两个卖点，且**都不含真实姓名**。
- **适合进模块截图墙的 10 张**：`p01…p10.png`（已拼成 `docs/assets/github/modules-wall.png`，见第四节）。**其中 3 张画面偏弱需留意**：`p06` 停在「加载中…」空态、`p07` 图表无数据条、`p01` 右栏是「加载订单列表失败」错误态——它们仍可作模块墙缩略，但不建议单独放大图。
- **只适合当证据链接的**：`portfolio.png`、`live-before-20261014.png`（旧版对照）、`portfolio-full.png`（含姓名且过长）、`portfolio-matrix/*` 全部 7 张（均含真实姓名）、`p05.png`（含明文口令）、`p06.png`（空态）。
- **长图不适合首屏直接铺**：`portfolio-full.png`(1280×3400)、`self-check-full.png`(1440×5600)（长宽比 <0.4，正文塞不下）。

---

## 三、安全结论（最重要 · 逐张核查）

**核查范围**：上表 23 张 PNG，逐张用 `read` 目视检查有无手机号 / 邮箱 / 真实姓名，并对高风险区域（`p05` 登录页底部、`portfolio-full` 作者区）另做裁剪放大复核。

1. **手机号：0 处。** 23 张图里**没有任何手机号**（无 11 位连续数字形态的号码）。
2. **邮箱：仅 1 处，且为占位符。** `p02.png` 邮箱输入框的灰字 `owner@example.com` 是**示例占位符**（`example.com` 为保留域名），不是真实邮箱。其余 22 张无邮箱。
3. **真实姓名：出现于 8 张，均为作者本人署名。**
   - `_evidence/portfolio/portfolio-full.png` → 底部作者区「**李奕波 · 2026** · 基于统一设计系统 shared/ui-kit 构建」。
   - `_evidence/portfolio-matrix/` 全部 **7 张** → hero 位置大字「**李奕波 / LI YIBO**」。
   - 这属于**作者对自己的作品集署名**，公开仓库里通常是有意为之；但**只要这些图进了 README 首屏，个人真实姓名即被公开展示**。→ **建议：README 首屏不要用这 8 张图；如要用 `portfolio-full.png`，先裁剪掉底部作者区。** 该取舍需作者本人确认（**我未做裁剪，也未改动源文件**）。
4. **明文凭据（不是手机号/邮箱，但同样敏感，必须点出）**：`_evidence/screenshots/p05.png` 在页面左下方明文印着「演示账号：`legal / applicant / admin`，初始口令分别为 `Legal@2026`、`Apply@2026`、`Admin@2026`」。这张图若进 README，等于把一套口令写进公开 README。→ **建议只作内部证据，或先涂抹该段文字再对外**。
5. **演示角色名（非真实姓名）**：`shell.png` 右上角显示「`张总（老板）` Owner」，是登录后的演示身份标签，**不是真实人名**，可放心。
6. 其余图（p01/p03/p04/p06/p07/p08/p09/p10、portfolio.png、live-before、portfolio-home、static-site-top、self-check-*）**无手机号、无邮箱、无真实姓名**。

> 一句话：**没有手机号，没有真实邮箱（唯一邮箱是 `owner@example.com` 占位），真实姓名只出现在作者署名类截图（portfolio-full + portfolio-matrix 七张）；另需注意 `p05` 含明文演示口令。**

---

## 四、`docs/assets/github/modules-wall.png` 生成说明

- **成品**：`docs/assets/github/modules-wall.png`，**1972 × 776 px，224,523 字节（约 219.3 KB）**，RGB，UTF-8 语境下中文用 `C:/Windows/Fonts/msyh.ttc`（微软雅黑）渲染，**无豆腐块**（已用 `read` 目视复核）。
- **构图**：浅色底 `#F5F7FA`；5 列 × 2 行；每格白底圆角卡 + 细边框 `#DDE2EA`；格内为对应模块截图（等比缩放到 346×222，加圆角与边框）；**每格下方标注 `P0X · 模块名` 与「来源 pXX.png」**，编号与图片一一对应，可据来源文件名复核。
- **来源文件（严格一一对应，不顶替、无留空）**：
  `P01←p01.png`、`P02←p02.png`、`P03←p03.png`、`P04←p04.png`、`P05←p05.png`、`P06←p06.png`、`P07←p07.png`、`P08←p08.png`、`P09←p09.png`、`P10←p10.png`（均在 `_evidence/screenshots/`）。
- **模块名与本仓库注册表口径一致**：P01 AI 电商客服 / P02 电商运营助手（旗舰）/ P03 NL2SQL 问数 / P04 RAG 知识库 / P05 合同审批 / P06 数据中台 / P07 AI 素材中心 / P08 直播切片 / P09 AI 销售考核 / P10 模型微调平台。
- **十个模块均有可用截图，无缺图、无留空位。** 但请一并知悉：如上表所述，`p06`（加载态）、`p07`（图表空）、`p01`（含报错）三格画面本身偏弱——**这不是拼接错位，是源图如此**。
- **复现命令**（脚本置于临时目录、不写入本仓库；源图只读）：
  ```powershell
  # 脚本内容见交付说明；核心：
  python "C:\Users\23329\AppData\Local\Temp\opencode\build_wall.py"
  ```
  脚本要点：Pillow 打开 `_evidence/screenshots/pXX.png` → `LANCZOS` 缩放到 346×222 → 圆角遮罩粘贴 → 圆角矩形画卡与边框 → `msyh.ttc/msyhbd.ttc` 写图注 → `save(..., "PNG", optimize=True)`。
- 源评估：**未对 `_evidence/` 下任何文件做写操作。**

---

## 五、README 可直接粘贴的组合片段

> 说明：GitHub 会剥离 `style=` 属性，下面**一律用 HTML 属性**（`width` / `align`）控制尺寸。路径相对仓库根。
> 隐私提醒：下列示例**刻意避开了含真实姓名与明文口令的截图**。

### (a) 两张图并排（首屏推荐：作品集浅色态 + 统一外壳深色态）

```html
<p align="center">
  <img src="_evidence/portfolio/static-site-top.png" width="49%" alt="李奕波个人作品矩阵 · 作品集首屏（浅色态）" />
  <img src="_evidence/screenshots/shell.png" width="49%" alt="统一外壳工作台：一个入口挂载十个模块（深色态）" />
</p>
<p align="center">
  <sub>左：作品集首屏（浅色）——每个数字都能在仓库里复跑，跑不通的地方直写「未跑通 + 原因」｜右：统一外壳（深色）——P01–P10 经同一网关按四层架构挂载</sub>
</p>
```

### (b) 十模块 5×2 截图墙

**方式一（推荐，直接用已生成的单张总览图，便于控制仓库体积）：**

```html
<p align="center">
  <img src="docs/assets/github/modules-wall.png" width="100%" alt="李奕波个人作品矩阵 Li Yibo's Personal Portfolio · 十大 AI 能力模块总览（P01–P10）" />
</p>
<p align="center">
  <sub>十大 AI 能力模块总览（P01–P10）· 每格注明来源文件名，可对照 <code>_evidence/screenshots/pXX.png</code> 复核</sub>
</p>
```

**方式二（原生 5×2 表格，指向十张原始图，可逐张点击放大）：**

```html
<table>
  <tr>
    <td align="center"><img src="_evidence/screenshots/p01.png" width="100%" alt="P01 AI 电商客服"><br><sub>P01 · AI 电商客服</sub></td>
    <td align="center"><img src="_evidence/screenshots/p02.png" width="100%" alt="P02 电商运营助手"><br><sub>P02 · 电商运营助手（旗舰）</sub></td>
    <td align="center"><img src="_evidence/screenshots/p03.png" width="100%" alt="P03 NL2SQL 问数"><br><sub>P03 · NL2SQL 问数</sub></td>
    <td align="center"><img src="_evidence/screenshots/p04.png" width="100%" alt="P04 RAG 知识库"><br><sub>P04 · RAG 知识库</sub></td>
    <td align="center"><img src="_evidence/screenshots/p05.png" width="100%" alt="P05 合同审批"><br><sub>P05 · 合同审批</sub></td>
  </tr>
  <tr>
    <td align="center"><img src="_evidence/screenshots/p06.png" width="100%" alt="P06 数据中台"><br><sub>P06 · 数据中台</sub></td>
    <td align="center"><img src="_evidence/screenshots/p07.png" width="100%" alt="P07 AI 素材中心"><br><sub>P07 · AI 素材中心</sub></td>
    <td align="center"><img src="_evidence/screenshots/p08.png" width="100%" alt="P08 直播切片"><br><sub>P08 · 直播切片</sub></td>
    <td align="center"><img src="_evidence/screenshots/p09.png" width="100%" alt="P09 AI 销售考核"><br><sub>P09 · AI 销售考核</sub></td>
    <td align="center"><img src="_evidence/screenshots/p10.png" width="100%" alt="P10 模型微调平台"><br><sub>P10 · 模型微调平台</sub></td>
  </tr>
</table>
```

**方式二注意事项**：`p05.png` 含明文演示口令、`p01.png` 含「加载订单列表失败」错误态、`p06.png` 为加载态空屏——若采用方式二，建议对 `p05` 先涂抹口令区（**本次未做任何涂抹或改图**），或改用方式一。

---

## 六、2026-10-15 复拍：浅色态现行界面（`docs/assets/github/screens/`）

> **为什么复拍**：第 3~5 节建档的 `_evidence/screenshots/pXX.png`、`shell.png` 是**浅色态改版之前**的界面（外壳那张还停在 `v0.1.0` 的深色「工作台」），把它们放在 README 首屏会与正文「白底 + 单一品牌蓝」的叙述自相矛盾。故于 2026-10-15 在**本机 15/15 服务在线**时重新实拍一套。

| 文件 | 像素 | 字节 | 画面内容 |
|---|---|---|---|
| `docs/assets/github/screens/shell-home.png` | 1212×1310 | 192 KB | 外壳统一入口首屏：作品集标题 + 六个实测指标（10 模块 / 4 层 / 731 passed / 4 条跨模块真实取数 / 6 条 ADR / 10-10 服务探活）+ 四层模块卡区起点 |
| `docs/assets/github/screens/p01.png` | 1200×1297 | 153 KB | P01 AI 电商客服对话页（「Hi，我是 听澜」+ 用户标识 u1001） |
| `docs/assets/github/screens/p02.png` | 1200×1272 | 52 KB | P02 运营助手登录页（四角色演示账号一键填充） |
| `docs/assets/github/screens/p03.png` | 1200×1272 | 88 KB | P03 NL2SQL 问数欢迎页（含「AI 生成结果可能存在偏差，请以下方溯源报告为准」） |
| `docs/assets/github/screens/p04.png` | 1200×1272 | 77 KB | P04 RAG 知识库上传页，顶部为**真实依赖探测**：Milvus / MongoDB / MinIO / BGE-M3 / LLM 全部在线 |
| `docs/assets/github/screens/p05.png` | 1200×1288 | 181 KB | P05 衡鉴 V2.1.9 登录页 + 三类角色一键进入 |
| `docs/assets/github/screens/p06.png` | 1200×1282 | 109 KB | P06 数据中台数据总览（14 张表 / 3.24 万行 / 健康分 29 / 四层分层 / 核心指标） |
| `docs/assets/github/screens/p07.png` | 1200×1297 | 81 KB | P07 AI 素材中心概览（17 素材 / ROI 10.25x / 类型分布 / 投放转化漏斗） |
| `docs/assets/github/screens/p08.png` | 1200×1282 | 101 KB | P08 直播切片数据概览（左下角常驻 `ASR / 评分 / 视频 均为模拟`） |
| `docs/assets/github/screens/p09.png` | 1200×1260 | 109 KB | P09 AI 销售考核看板（顶部常驻「LLM 评分使用基于规则的启发式算法」说明） |
| `docs/assets/github/screens/p10.png` | 1200×1272 | 73 KB | P10 模型微调平台总览（顶部常驻「训练、评测和部署均为模拟，未实际占用 GPU 资源」） |

- 合成图：`docs/assets/github/modules-wall.png`（1876×980，402 KB），由 `python -X utf8 _tools\make_readme_gallery.py` 从上面十张 `pXX.png` 生成（5 列 × 2 行、浅色底 `#F5F7FA`、白卡 + `#DDE2EA` 边框、`msyh.ttc` 中文图注）。脚本按编号与 `README` 第五/七章口径一一对应，**缺图即报错退出，不会留空位**。
- **品牌位差异（有意）**：截图中侧栏显示的是「李奕波个人作品矩阵」而不是「李奕波个人作品矩阵」，因为本机 `shared/config/brand.json`（品牌位真源、不入库）已被机主自定义。这恰好是第一章「品牌可自定义」的真实效果，README 第三节已就这一点写明。
- **隐私复核（本次复拍图）**：无手机号、无个人邮箱、无他人姓名。`p05.png` 页面内印有演示账号与口令 `legal / applicant / admin` + `Legal@2026 / Apply@2026 / Admin@2026`、`p02.png` 印有演示邮箱 `*@example.com` 与「密码均为 Test123456」—— 这些**与 README 第四章的演示账号表完全一致，属仓库已公开的本地种子凭据**，不是额外泄露；生产部署必须自设 `CP_AUTH_SECRET`。
- 复拍命令留档：用桌面浏览器工具逐页 `tabs.open` → 等异步数据渲染完成 → `screenshot(maxWidth=1200)`，服务状态来自 `python _tools\supervisor.py status`（实测 **15/15 在线**）。

---

_本文件由证据与截图策展（D 号）生成；所有画面结论均来自 `read` 工具目视，尺寸/字节来自 Pillow 实测。_
_第六节为 2026-10-15 整合阶段追加（复拍记录与合成脚本），第一至五节内容未改动。_
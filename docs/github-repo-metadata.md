# GitHub 仓库门面元数据方案（liyibo0410/yunshu-ai-portfolio）

> 本文件由「仓库门面元数据工程师」产出，配套落地脚本 `_tools/set_repo_metadata.py`。
> 目标仓库：`https://github.com/liyibo0410/yunshu-ai-portfolio`
> 撰写日期：2026-10-15 · 全部「实测」数字都标了来源，未实测的判断一律写明「未核对」。

---

## 0. 远端现状与本次要解决的问题

2026-10-15 用作者 Token 调 REST API 实测（本次又用未认证 `GET /repos/...` 独立复现过一次）：

| 字段 | 现状 | 说明 |
|---|---|---|
| `description` | **空**（`null`） | 浏览器里标题下没有任何一句话 |
| `topics` | **空**（`[]`） | 不受任何 topic 索引，等于不可被 topic 检索到 |
| `homepage` | **空**（`null`） | 右侧没有 Website 链接，在线演示入口不可见 |
| `stars` / `size` | 1 / 58,589 KB（≈ 57 MB） | size 偏大 → 新图要控制体积，见第 3 节 |
| `default_branch` | `main` | — |
| `private` | `false` | 公开仓库，未认证也能读 |

**要解决的就是上面三个「空」。** 另外 `liyibo0410/liyibo0410`（个人主页仓库）实测 **404 不存在** —— 门面还有「个人主页 README + Pinned」这一块，但那是 B 号（主页）与主控的事，本文件只给 Pinned 排序建议。

一句话结论：**本仓库目前是「内容很满、门面全空」**。读者点进来只能自己从 README 里刨；补完这三项，成本约 5 分钟，收益是「能被搜索到 + 一眼看懂是什么」。

---

## 1. About 简介候选 3 条

GitHub About 上限 **350 字符**（中文按 1 字符算，下面字符数用 Python `len()` 实测，与 GitHub 口径一致）。
三条都可直接复制粘贴。**推荐 A**（下面给了理由）。

### 候选 A —— 推荐，也是脚本内置的默认值（217 字符）

```
李奕波个人作品矩阵 Li Yibo's Personal Portfolio · AI 电商运营中台：10 个 AI 能力模块（AI 客服 / 电商运营助手 / NL2SQL 问数 / RAG 知识库 / 合同审批 / 数据中台 / 素材中心 / 直播切片 / 销售考核 / 微调平台）合并成一套统一系统——微前端外壳 + 统一认证 + 端口注册表 + 跨模块真实调用，731 passed。Python 3.12 · FastAPI · LangGraph · Next.js。
```

- **字符数：217 / 350**
- 结构：是什么（李奕波个人作品矩阵 · AI 电商运营中台）→ 多大规模（10 个能力模块，逐个点名）→ 最硬差异点（**合并成一套**统一系统：微前端外壳 / 统一认证 / 端口注册表 / 跨模块真实调用）→ 一条可复核的硬数字（731 passed）→ 技术栈。
- **不依赖任何上下文**：把 10 个模块名全列出来，即使读者从没听过这个项目、也没点进 README，也知道它是干什么的。
- 唯一略长的部分是把 10 个模块逐个点名（约 70 字符）；**这是刻意保留的** —— 这些模块名同时充当关键词：读者在 GitHub 搜「RAG 知识库」「NL2SQL」时，About 文本也参与站内搜索。

### 候选 B —— 强调「一套系统」的四层结构与证据纪律（243 字符）

```
十个 AI demo 合并成一套系统。李奕波个人作品矩阵 Li Yibo's Personal Portfolio · AI 电商运营中台：L0 数据中台 → L1 微调平台 → L2 能力层（NL2SQL 问数 / RAG 知识库 / 素材中心 / 直播切片）→ L3 应用层（AI 客服 / 电商运营助手 / 合同审批 / 销售考核）；15 个受管进程、6 条 ADR、4 条跨模块真实 HTTP 调用、731 passed，任何数字都能在 _evidence/ 复核；没做的（并发压测 / 覆盖率 / 真实训练）就写「未做」。
```

- **字符数：243 / 350**
- 与 A 的差别：开头一句「十个 AI demo 合并成一套系统」是**最锋利的一句差异点**，比 A 更早亮出来；把四层（L0→L3）摊平，架构一眼可见；把「未做的就写未做」写进 About —— 这是本项目最特别的一条纪律，也是最需要交代清楚的点。
- 代价：L0/L1/L2/L3 这类层号对非行内读者有理解成本，且没有技术栈关键字。

### 候选 C —— 最短、最强调「可复核」（184 字符）

```
AI 电商运营中台 · 李奕波个人作品矩阵 Li Yibo's Personal Portfolio：10 模块 / 4 层 / 15 个受管进程 / 731 passed。差异点不是功能多，而是每个数字都能在仓库里复核：mock 双处标注，没做并发压测就写「未做」，跨模块取数走真实 HTTP 且降级不伪造。Python 3.12 · FastAPI · LangGraph · Next.js · Vue 3。
```

- **字符数：184 / 350**
- 用 4 个数字开场（10 / 4 / 15 / 731），把「工程化 + 不吹」当卖点。适合你更想被当成「工程纪律型候选人」而不是「功能堆砌型」时用。
- 代价：4 个裸数字对陌生读者没有抓手，第一遍读会有点密。

### 为什么推荐 A

三条都不违规、都能独立成立。选 A 的理由是「**第一次点进来的人只有 3 秒**」：A 里既有 10 个模块的具体名字（让读者立刻看到自己关心的 RAG / NL2SQL / 微调），又有一句完整的架构差异点，且有技术栈。B 的金句更好，但把它放到 **README 第一段**（那里空间不受限）收益更大；About 这个位置更适合「说明书」而不是「金句」。

> A 与脚本里的 `DEFAULT_DESCRIPTION` **是同一份文本**（已逐字节核对）。要换候选，改 `_tools/set_repo_metadata.py` 的 `DEFAULT_DESCRIPTION` 常量，或命令行 `--description "..."` 覆盖。

---

## 2. Topics 建议（正好 20 个 = GitHub 上限）

全部小写、连字符、无空格。「仓库数」一列是 **2026-10-15 实测**：直接抓 `https://github.com/topics/<标签>` 页面上的 “Here are N public repositories matching this topic...” —— 这是真实数据，不是估计。

| # | topic | 该标签下的公开仓库数（实测） | 为什么这个标签能带来搜索曝光 |
|---|---|---|---|
| 1 | `python` | 963,941 | 站内语言过滤器与「python」关键词的基础盘；几乎所有人筛仓库第一步就是这个 |
| 2 | `fastapi` | 109,159 | 后端栈主关键词，中文 JD 里高频出现；搜 FastAPI 项目的人就是目标读者 |
| 3 | `llm` | 156,943 | AI 应用方向最主流的检索词，比 `ai` 精确、比 `gpt` 通用 |
| 4 | `rag` | 56,186 | 当前 AI 应用岗第一热词；RAG 类项目稀缺度仍高于需求量 |
| 5 | `ai-agent` | 39,785 | 比 `llm` 更精确指向智能体；GitHub 的 agent 类聚合页会收录 |
| 6 | `multi-agent` | 19,653 | 命中「多智能体编排」检索；本项目 10 模块 + 编排层确实是多体结构 |
| 7 | `langchain` | 27,773 | 生态标签：按框架名过滤的人会命中 |
| 8 | `langgraph` | 15,582 | 同生态但更聚焦编排；竞争度低于 langchain，容易被翻到 |
| 9 | `nl2sql` | 407 | **精准垂类**：全站只有 407 个仓库，做 NL2SQL 的人几乎必然翻到；不指望 topic 页流量，靠精确检索命中 |
| 10 | `llmops` | 3,573 | 直接对应「微调平台 + 模型注册表 + 评测」这套平台工程叙事，平台岗 JD 常用词 |
| 11 | `lora` | 6,587 | 对应 P10 的 LoRA 生命周期编排。**曾考虑 `model-finetuning`，实测全站只有 8 个仓库（几乎无曝光），故换成 `lora`** |
| 12 | `knowledge-base` | 7,776 | RAG 之外的自然语言同义词（中文语境里「知识库」比「RAG」更常用） |
| 13 | `micro-frontend` | 382 | **架构差异点标签**：全站仅 382 个，而「十个 demo 合并成一套系统」正是本项目最硬的差异点 |
| 14 | `nextjs` | 202,920 | 旗舰模块 P02 的栈；React 生态最高频检索词之一 |
| 15 | `vue3` | 20,053 | P01/P03/P04 前端栈；Vue 生态检索词，与 nextjs 一起覆盖两类读者 |
| 16 | `duckdb` | 6,131 | P06 数据中台的真实引擎；`duckdb` 话题下项目不多，冷门但高相关 |
| 17 | `milvus` | 668 | 向量库标签：按基建过滤 RAG 项目的人会命中 |
| 18 | `e-commerce` | 8,684 | 业务域标签，把项目锚定到具体行业；「电商 + AI」是可检索组合 |
| 19 | `docker` | 233,690 | 多服务编排 / 容器化，DevOps 向检索词 |
| 20 | `portfolio` | 90,105 | 明确定位「工程作品集」，且是真实存在的热门标签（实测 90k） |

**共 20 个，正好顶到 GitHub 上限。** 数字口径：**12** 个标签在 1 万以上（负责「被翻到」），5 个在 3k~10k（`llmops` / `lora` / `knowledge-base` / `duckdb` / `e-commerce`，负责「被精确命中」），3 个在 1k 以下（`nl2sql` 407 / `micro-frontend` 382 / `milvus` 668，负责「精准垂类」）。12 + 5 + 3 = 20。

### 必须删掉 / 不要用的标签（禁用清单）

这些标签**格式合法**，但加上去只会稀释定位。脚本里已内置拦截（`BANNED_TOPICS`，传进去直接报错）：

| 禁用标签 | 实测仓库数 | 为什么必须删 |
|---|---|---|
| `hacktoberfest` | 147,982 | 流量最大的一类「引流标签」，但来访者是来找**参与开源活动**的，不是来看项目的；本仓库也不收外部 PR |
| `awesome` | 12,574 | 语义是「资源清单 / 收藏夹」，会被当成目录页而不是可运行系统 |
| `awesome-list` | — | 同上，且与「一套统一系统」的定位冲突 |
| `good-first-issue` | — | 意思是「欢迎新人练手」，与「成熟作品集」定位相反 |
| `help-wanted` / `first-timers-only` | — | 暗示项目未完成 / 缺人手 |
| `hackathon` | — | 与项目定位不符 |
| `opensource` | — | 几乎无区分度，等于没打标签 |
| `ai` | — | 过宽，被海量仓库稀释；用 `llm` / `ai-agent` / `rag` 替代 |

### 候补 / 可替换标签（同样是实测数字，供你按关注点二选一）

| 标签 | 实测仓库数 | 什么时候换成它 |
|---|---|---|
| `text-to-sql` | 1,666 | 想覆盖英文检索词时替换 `nl2sql`（两者指同一能力，20 个坑位只够一个） |
| `vector-database` | 8,553 | 想强调向量基建时替换 `milvus` |
| `ragas` | 655 | 想突出「有评测」时替换 `knowledge-base`（但 Ragas 只是 P04 的一个评测工具，偏窄） |
| `vllm` | 3,415 | 若后续 P10 真接推理服务再换进来 |
| `tailwindcss` | 186,005 | 想加前端曝光可换掉 `duckdb` |
| `typescript` | 482,493 | 想加语言曝光可换掉 `docker` |
| `mysql` / `redis` | 113,378 / 45,632 | 想突出存储栈时可换掉 `milvus` |
| `agent` | 21,950 | `ai-agent` 已覆盖，重复度高，不推荐同时打 |
| `portfolio-project` | 10,271 | 比 `portfolio` 更精确但更冷门；想更贴近作品集语义时可换 |

> 20 个是硬上限，所以上面这些是**取舍**而不是「再多加几个」。想换就改脚本里的 `DEFAULT_TOPICS`（或 `--topics a,b,c`）。

---

## 3. Social preview（社交预览图）说明

**这是唯一不能自动化的项。**

| 项 | 值 |
|---|---|
| 尺寸 | **1280 × 640**（2:1，GitHub 官方推荐值） |
| 格式 | **PNG**（GIF/JPEG 也能传，但 PNG 在文字边缘最干净） |
| 体积 | **≤ 1 MB**（硬限制，超了会传不上去） |
| 上传路径 | 仓库页 → **Settings → General** → 滚到 **Social preview** → **Edit** → **Upload an image** |
| 关键限制 | **REST API 不支持设置 Social preview** —— 没有对应端点，只能网页点（脚本里也把这句话打了出来） |
| 生效范围 | 只对**本仓库**生效。个人主页（`github.com/liyibo0410`）的头像是另一回事 |
| 出现位置 | 分享链接到微信 / 飞书 / Twitter / Slack 时的卡片大图 |

**图片来源**：`docs/assets/github/social-preview.png` —— **已由 A 号用 `_tools/make_github_assets.py` 生成**，本次按字节实测核对如下（纯标准库解析 PNG 头）：

| 校验项 | 要求 | 实测 | 结论 |
|---|---|---|---|
| 尺寸 | 1280 × 640 | **1280 × 640**（比例正好 2.000） | ✅ |
| 格式 | PNG | PNG（8-bit，color type 2 = truecolor） | ✅ |
| 体积 | ≤ 1 MB | **133,418 字节 = 130.3 KB** | ✅ 余量 8 倍 |

同目录还有 `social-preview.svg`（4,755 字节）。**上传请用 `.png`**：GitHub 的 Social preview 上传框只接受位图（PNG / JPG / GIF），SVG 只能当源文件留着改图。
（同批产出的 `banner.svg` / `banner-dark.svg` / `modules-wall.png`（1876×980，401.8 KB）/ `screens/p01..p10.png` / `screens/shell-home.png` / `online-demo.md` / `SCREENSHOTS.md` 是 README 与主页用的，与 Social preview 无关。）

**给做图的人三条硬要求**（A 号这张已经满足，留存备改图时用）：

1. **别只放纯文字小字**：卡片缩略图最小可能只有约 300 px 宽，正文小于 28~32 px 就糊。核心字（比如「李奕波个人作品矩阵 · AI 电商运营中台」+「10 模块 / 731 passed」）要占满画面 1/3 以上。
2. **四周留 ≥ 48 px 安全边**：不同平台裁切比例不完全一致，贴边的内容可能被裁掉。
3. **控制体积**：57 MB 的仓库已经不小了，1280×640 的 PNG 若用照片级背景很容易超 1 MB。用纯色/渐变 + 文字（不要大照片）通常只有 100~300 KB。

---

## 4. Pinned repositories 建议（6 格排序）

> 前提说明：**Pinned 是「个人主页」的功能，仓库页没有 Pinned。** 所以在「仓库页」场景里，对应做法是在 README 里写一个「相关仓库」区块（因为根 `README.md` 不归本角色管，这里只给排序建议）。
> 另外 `liyibo0410/liyibo0410`（个人主页仓库）实测 **404 不存在** —— Pinned 要在个人主页出现，至少得先有主页 README 仓库（B 号 / 主控负责）。

只对给定的 6 个真实仓库排序。**注意：除 `yunshu-ai-portfolio` 外，其余 5 个仓库的内容我没有打开核对**，排序理由基于「仓库名 + `AGENTS.md` 里声明的来源关系」，见下方「不确定项」。

### 场景一：个人主页 `github.com/liyibo0410` 的 6 个 Pinned

| 位次 | 仓库 | 理由 |
|---|---|---|
| **1** | `yunshu-ai-portfolio` | 唯一「必看」项。它是把其余仓库的能力合并后的产物，也是唯一带 About/Topics 的主门面；放第一位 = 访客的第一跳 |
| **2** | `rag-knowledge-base` | RAG 是当前 AI 应用岗第一热词（topic 实测 56,186），而这是 P04 的来源仓库 —— 证明 RAG 能力不是 demo 而是「做过的原件」 |
| **3** | `customer-service-backend` | P01 的来源仓库，业务域最具体（客服 + 订单 + 商城），且有 FastAPI 后端 + Vue 前端全栈；与 1、2 形成「主项目 + 两个真实业务原件」的稳定三角 |
| **4** | `LangGraph-demo` | 框架能力证据链。LangGraph 对应本项目的多智能体编排（P02/P04 用到），topic 实测 15,582，竞争度低于 LangChain |
| **5** | `LangChain-demo` | 同上，`langchain`（27,773）是更主流的框架检索词；与第 4 位成对出现，读起来是「框架我按官方生态走过一遍」 |
| **6** | `-BOSS-RAG-` | 从名字看是另一个 RAG 变体，与第 2 位能力重叠、且仓库名以连字符开头（URL 可读性差、易被误认为 fork）。放末位，起「同方向练过多次」的补充作用 |

**排序逻辑**：第 1 位是「结论」，第 2~3 位是「结论的原始素材」（有真实业务），第 4~5 位是「框架熟练度」，第 6 位是「同方向的额外练习」。前 3 位决定了 80% 的印象，所以把「主项目 → 最热能力 → 最具体业务」放在最前。

### 场景二：仓库页（`yunshu-ai-portfolio` 的 README「相关仓库」区块）

仓库页没有 Pinned，读者已经站在主仓库里了，所以**不要重复「回到主项目」**。建议只列 3 个，顺序：

| 位次 | 仓库 | 理由 |
|---|---|---|
| 1 | `rag-knowledge-base` | 主仓库里 RAG（P04）是评测最完整的一块（有 Ragas 对照表），指向原件最有说服力 |
| 2 | `customer-service-backend` | P01 的来源，且主仓库里 P01 的已知限制最多 —— 想深挖的人应该去看原件 |
| 3 | `LangGraph-demo` | 想复现编排思路的人的第二跳 |
| （4~6） | `LangChain-demo` / `-BOSS-RAG-` / — | 建议**不列**。仓库页的相关链接超过 3 个就开始稀释；这两个更适合留在个人主页 Pinned 里 |

> 若你是想「把 6 个人主页 Pinned 也让仓库页读者看到」，正确做法是在 README 顶部加一个 `## 相关仓库` 小节，而不是换顺序。

### 不确定项（如实标注，建议主控复核）

- **仓库与模块的对应关系我只做了名称推断**，没有打开这 5 个仓库的正文核对：
  - `rag-knowledge-base` ↔ `AGENTS.md` 里 P04 的来源 `knowledge_base`（名字相近，**高置信但未核对**）
  - `customer-service-backend` ↔ P01 的来源（名字完全一致，**高置信**）
  - `LangChain-demo` / `LangGraph-demo` / `-BOSS-RAG-` —— `AGENTS.md` 的来源表里**没有提到**这三个，它们的定位完全来自仓库名（**低置信**）
- `-BOSS-RAG-` 的仓库名以 `-` 开头，我**没有验证**它在 URL 里是否需要转义、以及 GitHub 上显示成什么；位次 6 的判断也可能因此偏保守或偏乐观。
- 账号共 11 个公开仓库，但任务只给了 6 个名字。**排序只覆盖这 6 个**，其余 5 个没有评价依据（我没看过）。

---

## 5. 可选增强（**需你手动点，我不代做**）

| 项 | 建议 | 要点 |
|---|---|---|
| **About 右侧 Website 填在线演示链接** | **建议填，但要知道它是「开关式」的**（脚本已默认填 `http://39.96.200.45:8070`） | ① 这是「点开就能看」的入口，远比截图有说服力；② **它不是常态在线**：2026-10-15 **09:40 实测通、09:54 同一批入口全部 502**（服务器 nginx 在，上游 SSH 反向隧道已断），逐条记录见 A 号的 `docs/assets/github/online-demo.md`。挂着 Website 而入口 502，比不填更减分 —— 所以**演示当天先 `python _tools/tunnel_remote.py start`（自校验通过才发链接），再让读者点**；③ 它是 HTTP + 裸 IP：GitHub 允许，部分浏览器/内网会提示不安全；④ 演示结束建议 `--homepage ""` 清空（`_tools/tunnel_remote.py` **无自动超时机制**，忘了 `stop` 就是持续暴露公网 + 持续挂着一个死链接）；⑤ 别把模块页 `.../pXX/` 填进 Website，只填外壳首页 |
| **Add topics** | **建议做**（脚本已做，20 个） | 手动路径也在仓库页右上 ⚙/About 区域 → **Add topics**；但注意**手点一次上限也是 20**，和脚本口径一致。手动加时不要粘带空格的字符串 |
| **要不要打 Release / Tag** | **值得打 1 个 `v1.0.0`，但不值得建发版节奏** | **支持打**：本仓库的门面叙事是「731 passed / 6 ADR / 10 模块」，需要一个不可变快照点让读者下载对照；打 1 个 annotated tag + 写 3~5 行 Release notes（带上 `_evidence/regression-20261014-pytest.log` 链接）成本约 1 分钟，收益是「看着收尾了」。**不支持**建持续发版：CHANGELOG / CONTRIBUTING / 多版本 tag 对一个个人作品集是多余仪式，反而像套模板。**注意**：打 tag 不会让第 9 章的未闭环项（P08 不产切片、P10 未真实训练、未做并发压测）消失，别把 tag 当成「已交付」。另：tag/push 属于写操作，本角色不执行 |
| **README 顶部图片（camo 代理注意事项）** | 见下方 | 本仓库 D24 已经踩过一次同类坑：第三方 JS 原走公网 CDN，首屏要等 3.9~8.8 秒，最后全部落到 `shared/vendor/`。**README 图片同理，能放仓库里就别放公网** |
| **个人主页仓库 `liyibo0410/liyibo0410`** | 需先创建 | 实测 404；没有它就没有「个人主页」，Pinned 与主页 README 都无从谈起（B 号 / 主控负责内容） |

### README 顶部图在 camo 代理下的注意事项

先分清两类图片，它们的加载路径完全不同：

1. **仓库内相对路径**（如 `docs/assets/github/social-preview.png` 或 `![](./docs/assets/hero.png)`）
   → GitHub 直接从自家 CDN 提供，**不走 camo**。最稳，**强烈推荐**。也顺便把仓库当图床，不会因为外站挂掉变破图。
2. **公网外链**（如 `https://img.shields.io/...` 徽章、外部图床）
   → GitHub 会把 markdown 里的外链图片重写成 `camo.githubusercontent.com` 的代理地址。读者不需要能访问源站，但**camo 必须能访问源站**。这条链上的注意事项：
   - **源站不可达 / 返回非图片 / 被 camo 拉黑 → 破图**（读者看到的是坏掉的图标，而不是报错）。徽章类走 shields.io 时，如果 shields.io 抽风，README 顶部就会花掉。
   - **camo 以图片 URL 为 key 缓存**：同一 URL 换了图片内容，短时间内仍是旧图；要立刻刷新得给 URL 加个查询串（`?v=2`）。
   - **HTTPS 证书有问题的源站会被拒**。GitHub 页面是 HTTPS，图片也由 camo 用 HTTPS 回给浏览器，所以不存在混合内容问题 —— 但 camo 抓不到源站时就是破图。
   - **体积与大图**：仓库现在已 58,589 KB（≈ 57 MB）。README 顶部大图建议 ≤ 400 KB、宽度 ≤ 1600 px，否则 clone 时间变长（读者不一定 clone，但 `git clone` 体验会变差）。
   - **动图（GIF）**：会被 camo 原样代理，但动图常常几百 KB~数 MB，建议只放 1 张、且只截关键几秒。
   - **别用 `?sanitize=true` 之外的特殊参数**去规避缓存：不保证生效，且会让 URL 变脆。
   - 一句话规则：**能进仓库的就进仓库**（相对路径），徽章外链只留 3~6 个常用的、且都来自 shields.io 这类稳定源。

> 上面关于「源站抽风 → 破图」「URL 变 key 缓存」是 camo 的通用行为；**「本仓库的 README 具体有哪几张外链图」我没有逐一点开核对**（根 `README.md` 不归本角色管，且它有未提交的改动）。徽章现在是 6 个 shields.io 链接 + 2 个 mermaid 图，mermaid 是 GitHub 原生渲染、不走图片代理。

---

## 6. 落地方式（脚本怎么跑）

```powershell
# 0) 先看自检（不联网、不需要 Token）
python -X utf8 _tools\set_repo_metadata.py --self-test

# 1) dry-run：联网只读，打印现状 + 差异 + 将要发送的 body（不写任何东西）
python -X utf8 _tools\set_repo_metadata.py --repo liyibo0410/yunshu-ai-portfolio

# 2) 真写（需要作者 Token；Token 只放环境变量，不要写进任何文件）
$env:GITHUB_TOKEN = 'github_pat_...'
python -X utf8 _tools\set_repo_metadata.py --repo liyibo0410/yunshu-ai-portfolio --yes
#    写完会再 GET 一次，回读并打印实际生效的 description / topics / homepage

# 3) 只想换主题词 / 换简介
python -X utf8 _tools\set_repo_metadata.py --topics "ai-agent,rag,nl2sql"
python -X utf8 _tools\set_repo_metadata.py --description "..."

# 4) 演示结束，清掉会失效的 Website
python -X utf8 _tools\set_repo_metadata.py --homepage "" --yes
```

Token 要求：fine-grained Token 需 **Administration: write**（改 topics 需要）；经典 Token 需 `public_repo`（或 `repo`）范围。脚本会把 Token 打码成 `github_pat_11B4...izG4` 再打印，**从不回显完整值、从不写盘、不接受 `--token` 明文参数**。

---

## 7. 待办清单（谁来做）

| # | 事项 | 自动化（脚本能做） | 手动（只能网页做） | 备注 |
|---|---|---|---|---|
| 1 | About 简介（候选 A，217 字符） | ✅ `PATCH /repos/{repo}` 的 `description` | 也可在仓库页 About 右侧铅笔图标改 | 脚本内置 `DEFAULT_DESCRIPTION`；换候选用 `--description` |
| 2 | Website 链接 `http://39.96.200.45:8070` | ✅ `PATCH /repos/{repo}` 的 `homepage` | 同上，About 右侧 **Edit** | ⚠️ **并非常态在线**：2026-10-15 09:40 实测通、09:54 全部 502。演示前必须先起隧道；演示后建议 `--homepage ""` 清空 |
| 3 | 20 个 Topics | ✅ `PUT /repos/{repo}/topics`（body `{"names":[...]}`，须带 `Accept: application/vnd.github+json`） | 也可在 About 区 **Add topics** | 上限 20；手点也一样 |
| 4 | Social preview 图 | ❌ **REST API 不支持** | ✅ Settings → General → **Social preview** → Edit → Upload an image | 图**已就位**：`docs/assets/github/social-preview.png` = 1280×640 / PNG / 130.3 KB（实测，三项全部合规）；**上传请用 .png 而不是同目录的 .svg** |
| 5 | 个人主页 6 格 Pinned | ❌ 无对应 API（Pinned 是 UI 顺序，GraphQL 有 `pinnedItems` 但**只能读**） | ✅ 个人主页 → **Customize your pins** | 排序见第 4 节场景一 |
| 6 | 仓库页「相关仓库」链接 | ❌ | ✅ 改根 `README.md`（**不归本角色，需主控/A 号**） | 排序见第 4 节场景二；根 README 现有未提交改动 |
| 7 | 创建 `liyibo0410/liyibo0410` 主页仓库 | ❌ | ✅ 新建仓库（名字必须与用户名一致才会显示为主页） | 实测 404 不存在；内容归 B 号 |
| 8 | 打 `v1.0.0` tag / Release | ⚠️ 有 API（`POST /repos/{repo}/releases`），但**要推 tag**，属写操作且应由作者决定 | ✅ 或网页 Releases → Draft a new release | 建议只打 1 个，不建发版节奏；本角色不执行 |
| 9 | 改完后核对生效 | ✅ 脚本自带回读（GET 后打印三项） | ✅ 直接开仓库页看 | dry-run 与真跑都会打印「差异」；远端已一致时显示「无差异」 |
| 10 | Topics 与本文档保持同步 | ✅ 文档表格 ↔ 脚本 `DEFAULT_TOPICS`（现均为同一组 20 个，顺序也一致，已逐项核对） | — | 改一处记得改另一处，别让门面和脚本打架 |
| 11 | 真发请求时的鉴权 | ⚠️ 脚本用环境变量里的 Token（`--token-env` 可改名），**用完请 `Remove-Item Env:GITHUB_TOKEN`** | — | 本机**未认证**配额很容易被出口 IP 上的其他用户耗尽（实测撞到 403），所以真跑请一定带上 Token |

---

## 附：本文件的实测边界

- 「仓库数」是 2026-10-15 抓 `https://github.com/topics/<标签>` 页面得到的**当天快照**，会随时间变化；标签**是否存在**是确认过的（页面正常返回并带 `Here are N public repositories`）。
- 远端 `description` / `topics` / `homepage` 为空的结论，本次用**未认证** `GET https://api.github.com/repos/liyibo0410/yunshu-ai-portfolio` 独立复现过一次（`description: null`、`homepage: null`、`topics: []`、`stars: 1`、`size: 58589`、`default_branch: main`、`private: false`）。
- 第 4 节 5 个仓库的内容与「来源对应关系」**未核对**，仅按名字 + `AGENTS.md` 推断，已在那一节逐条标注置信度。
- `docs/assets/github/social-preview.png` 与 `_tools/make_github_assets.py` 在撰写本文件时**尚不存在**；在收尾前 A 号已产出，故第 3 节的尺寸/格式/体积三项**改为按 PNG 头实测**（1280×640 / truecolor / 133,418 字节）。
- 在线入口我在本文件里**没有亲自发起请求**（引用的是 `AGENTS.md` 与 `docs/assets/github/online-demo.md` 记录的 09:40 通 / 09:54 502）。
- 脚本的失败分支是**真跑出来的**，不是推断：① 伪造 Token → GitHub 回 `401 Bad credentials`，脚本打人话 + 退出码 2（无 traceback）；② 本机出口 IP（`200.180.162.15`）的**未认证**配额被耗尽时 → GitHub 回 `403 API rate limit exceeded`，脚本打人话并把「推演的将发请求体」打出来 + 退出码 2；③ 本机代理一度断到 `api.github.com` 连不上（`WinError 10060`）→ 脚本打「网络层错误 + 排查建议 + 未发送任何写请求」+ 退出码 2。这三条在 `--self-test` 里都有离线回归用例（第 9 组）。
- 因此**完整版的 dry-run 差异输出（现状 / 差异 / 两个 body 全打出来）是在配额耗尽前抓的那一次**；限流之后只能看到「读不到现状」分支。
- 未执行任何写 GitHub 的操作：只跑了 `--self-test`、未认证 dry-run、以及一次带**伪造** Token 的 dry-run（用于验证 401 人话提示）。**没有**带真 Token 跑过 `--yes`。
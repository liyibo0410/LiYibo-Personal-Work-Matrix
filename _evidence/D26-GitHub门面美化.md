# D26 · GitHub 门面美化（仓库 README + 个人主页 + 门面元数据）

> 日期：2026-10-15 · 执行：1 名主控 + 4 名并行智能体（视觉资产 / 个人主页 README / 门面元数据 / 截图策展）
> 纪律：本轮**只在本地产出文件，未 `git commit`、未 `git push`**（等机主审阅）；未改动 `_evidence/` 下任何已有文件的字节。

## 0. 机主的四条决策（决定了本轮边界）

| 问 | 决策 |
|---|---|
| 美化范围 | 仓库 README（yunshu-ai-portfolio）+ 个人主页 README（liyibo0410）+ 仓库门面元数据（**三项全选**） |
| 发布到哪一步 | **只本地产出，先审阅** —— 不 commit、不 push |
| 工作区那批未提交的 D24/D25 改动 | **不动它们**，只处理美化相关文件 |
| 口径不一致 | 一起修，**以 README 的 731 为准** |
| 个人主页仓库怎么建 | 机主提供 Token，主控走 API 建（**本轮尚未执行建仓/推送**） |

## 1. 远端现状（实测，非转述）

用机主 Token 调 `api.github.com`（2026-10-15）：

- `liyibo0410/yunshu-ai-portfolio`：`description` **空**、`topics` **空**、`homepage` **空**、`stargazers_count` 1、`size` 58589 KB、`default_branch` main。
- `liyibo0410/liyibo0410`（个人主页仓库）：**404，尚不存在** —— 所以个人主页目前没有任何 README 展示。
- 账号共 11 个公开仓库。
- 本机 `gh` CLI **未安装**；仓库 `.env` 里**没有** GitHub Token（故走 API 需临时传入，**未落盘、未写进任何文件**）。

## 2. 主控自己做的事（不在四名智能体名下）

### 2.1 README.md 重写（25.4 KB → 18.2 KB，结构重排而非删内容）

- 顶部 `<picture>` 壁纸（深浅色自动切换）+ 7 枚静态徽章 + 4 条快捷入口（截图 / 本地跑 / 数字 / 面试路线 / 证据索引）。
- 新增 **「三十秒速览」** 表（是什么 / 多大规模 / 最硬差异 / 最想被追问 / 怎么验 / 作者）与**目录**（12 条锚点，已用脚本核对全部命中对应标题）。
- 新增 **第三章「平台长什么样（截图）」**：外壳首屏 + 十模块截图墙，并点明「照片里就能看到 Mock 标注」。
- 保留原有全部内容：架构双 mermaid、快速开始与演示账号、十模块表、可复核数字（测试 731 + 四份评测 + 四条跨模块链路）、真实/模拟边界、两个缺陷根因、6 条 ADR、已知限制、目录与证据、面试路线。

### 2.2 三处「口径/事实」修正（都属于「数字必须能复核」这条纪律）

| # | 原表述 | 实测后改为 | 依据 |
|---|---|---|---|
| 1 | README 第五章链路写「负面情绪建单转人工」、第七章 P01「真实」列含「转人工建单」；`README:137` 同 | 链路改为 `human_handoff` **流程**；并显式写明**「负面情绪自动建单」整链不存在**（全仓无情绪判定与建单代码） | `grep -r "sentiment\|建单" projects/p01-ai-customer-service` → 仅 1 处无关文档命中；`flow_config/user_flows.yml:229` 只有 human_handoff 流程 |
| 2 | AGENTS.md 写「全平台 705 passed」，README 写 731 | AGENTS.md 补注：705 是 **D24 基线**，+ 当晚四个切片（P01 62→73 / P02 171→178 / P09 51→55 / P10 31→35）= **731**；README 第六章把两次实跑的跑法与日志名写清 | `_evidence/regression-20261014-pytest.log`（705 逐模块行）+ 四个切片日志；731 与逐模块相加一致（73+178+137+59+48+48+68+30+55+35） |
| 3 | README 第十.6 与 AGENTS.md 写公网入口「已打通」 | 补上**它不是常态在线**：2026-10-15 09:40 实测可开、09:54 复测**全部 502**（服务器 nginx 在、上游隧道断）；README 只写「按需开启、演示时段有限」 | 主控 09:40 的 webfetch 成功返回作品集首页；策展智能体 09:54 用 curl 逐条复测 7 个公网 URL 全 502，逐条记录落 `docs/assets/github/online-demo.md` |

> 另修正一处 P01 测试数：第五章表与第七章 P01 行从「62 单测」改为「73 单测」（知识检索 stub 已实装，见 AGENTS.md ⑧ 同批改口）。

### 2.3 本机实拍 11 张**浅色态现行界面**（替换掉浅色改版前的深色留档）

- 前提：`python _tools\supervisor.py status` 实测 **15/15 在线**；用桌面浏览器逐页 `tabs.open` → 等异步数据渲染完成 → `screenshot(maxWidth=1200)`。
- 产出：`docs/assets/github/screens/shell-home.png` + `p01.png`~`p10.png`（十张）+ 合成图 `docs/assets/github/modules-wall.png`（1876×980，402 KB，脚本 `_tools/make_readme_gallery.py`）。
- **为什么必须复拍**：原 `_evidence/screenshots/pXX.png` / `shell.png` 是浅色态改版前的深色界面（`shell.png` 还停在 `v0.1.0` 深色工作台），放进 README 会与正文「白底 + 单一品牌蓝」自相矛盾。
- 复拍图里有三张正好拍到了「诚实标注」本身：P08 的 `ASR / 评分 / 视频 均为模拟`、P09 的「LLM 评分使用基于规则的启发式算法」、P10 的「训练、评测和部署均为模拟，未实际占用 GPU 资源」，P04 顶部是真实依赖探测（Milvus / MongoDB / MinIO / BGE-M3 / LLM 全在线）。
- **品牌位差异已写明**：截图侧栏显示「李奕波个人作品矩阵」，因为本机 `shared/config/brand.json`（品牌位真源、不入库）被机主自定义过；默认值仍是「云枢智能」。README 第三章与 `SCREENSHOTS.md` 第六节都把这条写成「品牌可自定义」的证据，而不是假装一致。

### 2.4 整合期自检（脚本化，可复跑）

- README 全部本地链接与图片路径：**缺失 0**（`![](…)`、`<img src>`、`<source srcset>` 三类都扫）。
- 目录 12 条锚点 vs 19 个标题：**不匹配 0**（按 GitHub slug 规则换算）。
- 5 份 SVG（A 的 3 份 + B 的 2 份）：均为合法 XML、无 `<script>` / `<foreignObject>` / `@import` / 外链字体、尺寸与 viewBox 正确。
- 未提交改动核对：`git status` 里本轮只新增 `docs/assets/`、`docs/profile-readme/`、`docs/github-repo-metadata.md`、`_tools/make_github_assets.py`、`_tools/set_repo_metadata.py`、`_tools/make_readme_gallery.py`，并修改 `README.md` / `AGENTS.md`；**其余改动（含另一路并行会话今天在 `projects/p03`、`p04`、`p06` 上修的代码）一律没碰**。

## 3. 四名智能体的交付

见 `docs/assets/github/README.md`（视觉资产）、`docs/profile-readme/如何使用.md`（个人主页）、`docs/github-repo-metadata.md`（门面元数据）、`docs/assets/github/SCREENSHOTS.md` + `online-demo.md`（截图与入口实测）。

## 4. 尚未做的事（不要当成已完成）

1. **未 `git commit` / 未 `git push`** —— 等机主审阅通过。
2. **个人主页仓库 `liyibo0410/liyibo0410` 未创建**，`docs/profile-readme/README.md` 仍是本地文件（需机主最终点头）。
3. **仓库 About / Topics / Homepage 仍是空的** —— `_tools/set_repo_metadata.py` 默认 dry-run，未带 `--yes` 实跑。
4. **社交预览图需在网页上传**（`Settings → General → Social preview`），REST API 不支持；图已生成好放在 `docs/assets/github/social-preview.png`。
5. **README 尚未在 GitHub 真站渲染复核**（`<picture>` 深浅切换、手机端宽度、SVG 经 camo 代理后是否正常）—— 需要 push 之后才能看。
6. 头部横幅与社交预览卡上各有一处 `39.96.200.45:8070`（在线演示地址）：**该入口 09:54 实测 502**，是否保留在封面上待机主决定。
7. 个人主页 README **未放手机号**（正文只有 GitHub / 邮箱 / 城市 / 到岗时间），机主可在文末 HTML 注释处自行决定。
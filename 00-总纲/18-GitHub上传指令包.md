# GitHub 上传指令包（阶段成果固化）

- 日期：2026-10-12 · **D4 阶段结束，首次上传**
- 仓库位置：`D:\software\PycharmProjects\面试项目`（作品集根目录，单体仓库）
- 当前状态：**尚无 `.git`**（只有 `.gitignore`），需要从零初始化

---

## 一、先做安全检查（P0 亲自确认，不可跳过）

`.gitignore` 已排除 `.env`（含**真实 API Key**）、`*.db`、`*.log`、`projects/*/data/`。
我本轮又补了 `*.db-shm` / `*.db-wal`。

**上传前必查（在根目录执行）**：

```bash
git status --porcelain | grep -iE "\.env$|\.env\.|credential|token|secret" ; echo "--- 应为空 ---"
git check-ignore -v .env ; echo "--- 应显示被 .gitignore 命中 ---"
```

若第一条有任何输出，**立刻停手**，先把它加进 `.gitignore` 再继续。

---

## 二、仓库已建 + ⚠️ 可见性决策（P0 请先定这个）

**仓库**：`https://github.com/liyibo0410/yunshu-ai-portfolio.git`

**✅ 可见性已确认 Private**（2026-10-12 18:57，P0 操作完成）。
P1 复验方式：未认证 GET 该仓库 API 返回 **404 Not Found** ——
GitHub 对私有仓库统一返回 404（而非 403），以免暴露仓库存在性，这是转私成功的正常表现。

**结论：脱敏步骤（二·五节）本次不需要执行**，直接进入第三节首传。
（二·五的扫描结论与脱敏指令保留备查：将来若转公开，按该节执行即可。）

> 认证方式二选一（若本机没配过 git 凭据）：
> - **SSH**（推荐）：`git@github.com:liyibo0410/yunshu-ai-portfolio.git`
> - **HTTPS + Personal Access Token**：GitHub → Settings → Developer settings →
>   Tokens (classic) → 勾 `repo` → 生成后作为 push 时的密码

---

## 二·五、上传前敏感信息扫描（P1 已于 2026-10-12 执行）

扫描范围：全库（排除 `node_modules` / `.venv` / `.next` / `data/`）。

| 检查项 | 结果 | 判定 |
|---|---|---|
| 真实 API Key（`sk-xxxx` 长串） | 文档区 **0 命中**（只有 `sk-sp-` / `sk-ws-` 前缀说明） | ✅ 安全 |
| `.env`（含真实 Key） | 已被 `.gitignore` 排除 | ✅ 安全 |
| SSH 口令（本机已知弱口令串，**字面量不在本文档写出**） | **全库 0 命中**，无 `root@` / `password` 组合 | ✅ 安全 |
| **公网服务器 IP `39.96.200.45`** | **出现在 26 个文件**（P05 的 `deploy/` 8 + `verify/` 8 + 总纲 3 + 其它 7） | 🟡 **中危** |
| 专属工作空间端点 `ws-amdqcpdtt4gdo5ax...` | 出现在 `09-凭据与套餐配置说明.md` | 🟡 低（账户标识，非密钥） |

**结论**：无致命泄露（无明文密码、无真实 Key），**唯一实质风险是公网 IP 暴露** ——
IP 一旦公开可能被扫描端口。你服务器上跑着 8070/8090/8100/8110/8120 等多个站点，
且是已知的弱口令体系，建议不要裸奔。

**若选 B（保持 Public），请先让 Qoder 执行脱敏**：

```
【可选·脱敏】仅在 P0 决定保持公开仓库时执行

1. 把 P05 部署脚本与日志里的真实 IP 替换为占位符：
   在 projects/p05-contract-review/deploy/*.py 与 verify/remote_*.txt、
   *_perf.txt 中，把 39.96.200.45 替换为 <SERVER_IP>
   （脚本改读 .env 的 SERVER_IP 更好，但最小改动是先占位符化）

2. 把部署日志加入忽略（它们本来就属于运行产物）：
   .gitignore 追加：
     projects/p05-contract-review/verify/remote_*
     projects/p05-contract-review/verify/*_perf.txt
     projects/p05-contract-review/verify/remote_deploy.log

3. 复核：
   grep -rn "39.96.200.45" --exclude-dir=node_modules --exclude-dir=.venv . | wc -l
   期望：大幅下降（总纲里保留 1-2 处占位说明可接受）
```

---

## 三、给 Qoder 的上传指令（整段粘贴）

```
【任务】把作品集目录初始化为 Git 仓库并推送到 GitHub（首次上传，D4 阶段成果固化）

【仓库根目录】D:\software\PycharmProjects\面试项目
【远程地址】https://github.com/liyibo0410/yunshu-ai-portfolio.git
【分支】main

【前置确认】仓库已由 P0 转为 **Private**（已复验），
   **不需要执行脱敏步骤**，直接按下面 6 步执行首传即可。

【严格按顺序执行，每步都要打印结果给我看】

1. 初始化：
   cd "D:\software\PycharmProjects\面试项目"
   git init
   git branch -M main

2. 【安全红线】先确认凭据文件不会被提交，逐条执行并把输出贴给我：
   git check-ignore -v .env
   git status --porcelain | findstr /I ".env"
   期望：第一条显示 .gitignore 命中；第二条无输出。
   如果 .env 出现在待提交列表里，立刻停止并告诉我，不要继续。

3. 添加远程：
   git remote add origin https://github.com/liyibo0410/yunshu-ai-portfolio.git
   git remote -v        （确认只有一条 origin）

4. 暂存与首次提交：
   git add .
   git status --porcelain | findstr /I ".env"     （再次确认，应无输出）
   git commit -m "feat: 云枢智能作品集 Phase 0-D4

   - 00-总纲：12 份总纲文档（总纲提示词/资源清单/体检报告/工具链分工/
     算力方案/执行手册/凭据说明/模型资产/清理清单/协作流程/派活指令包/同步备忘录）
   - projects/p02：云枢智能电商运营助手（合规检测/深色化/权限守卫/列表页/llm-gateway）
   - projects/p05：衡鉴 V2.1.9 合同审查（D4-01 传输层状态码修复 + LLM 二阶段语义复核）
   - _evidence：验收报告与可复现验证脚本（P02 162 tests / P05 66+37 项）
   - shared：llm-gateway 共用库"

5. 推送：
   git push -u origin main

6. 收尾确认，把输出贴给我：
   git log --oneline -5
   git ls-files | findstr /I ".env" ; echo "应为空"
   git ls-files | wc -l          （应约 400-600 个文件）

【硬约束】
- 绝对不要把 .env 提交上去（含真实 API Key），任何一步发现它进了暂存区就停下报告
- 不要 git add -f 任何被 .gitignore 排除的文件
- 不要提交 projects/*/data/ 下的运行时数据库与上传的合同附件
- 不要执行 git push --force
- 如果 push 报认证失败，把完整报错贴给我，不要自行改用 --force 或跳过 hooks
```

---

## 四、后续每次阶段结束的上传 SOP（固化流程）

```
阶段结束（如 D5/D6/D7/D8 或任一里程碑）
  ↓
P1 完成验收 → 产出 _evidence/<模块>/验收报告.md
  ↓
P1 提醒 P0：「阶段结束，可以让 Qoder 上传 GitHub 了」
  ↓
P0 让 Qoder 执行增量提交（下面这段指令）
  ↓
Qoder 提交前仍须跑 .env 安全检查（第 2 步）
  ↓
push → 把 git log 贴回给 P1 存档
```

**增量提交指令（后续阶段用这段）**：

```
【任务】增量提交并推送（<阶段名> 阶段成果）

cd "D:\software\PycharmProjects\面试项目"

1. 安全红线检查（必做，贴输出给我）：
   git status --porcelain | findstr /I ".env"      ← 应无输出

2. 查看改动：
   git status
   git diff --stat

3. 暂存并提交（提交信息写清楚阶段与内容）：
   git add .
   git commit -m "<阶段>: <一句话概括>"

4. 推送：
   git push

5. 贴输出给我：git log --oneline -5

【硬约束】.env 绝不入库；不用 --force；不改 hooks
```

---

## 五、注意事项

| 项 | 说明 |
|---|---|
| 仓库规模 | 预计 400–600 个文件（不含 `node_modules` / `.venv` / `data/`，均已被忽略） |
| 大文件 | `samples/` 下的示例合同（PDF/PNG）合计约 1 MB，可以入库 |
| 证据目录 | `_evidence/` 保留（验收报告 + 验证脚本是作品集的重要资产），但 `*.log` 与 `raw/` 已忽略 |
| 私有/公开 | 建议先 Private；面试前确认无真实凭据残留后再考虑公开 |
| README | 根目录已有 `README.md`，会被一并提交，建议上传前让 Qoder 核对一遍内容是否最新 |

---

## 五·五、首传后 P1 复核记录（2026-10-12 19:05）

Qoder 报「6 步完成」后，P1 按红线「不接受口述」做独立复核（读本地 `.git` 元数据，不依赖 Qoder 转述）：

| 复核项 | 结果 |
|---|---|
| commit / 远程 | `ac08668` ✓ / `origin` 唯一且地址正确 ✓ |
| 已提交文件数 | 807 ✓ |
| **真实 `.env` 是否入库** | **否** —— 仅 3 个 `.env.example` 模板 + `alembic/env.py` + `dotenv_min.py` ✅ |
| `node_modules` / `.venv` / `data/` / `.next` / `__pycache__` | **全部 0 入库** ✅ |
| **已提交内容中的真实 API Key**（`sk-[A-Za-z0-9]{20,}`） | **0 命中** ✅ |
| 已提交内容中的明文口令 | 1 处（见下）⚠️ |

### 复核发现并修复的 2 个问题

**① 文档自身泄露 SSH 口令字面量（P1 自己造成的，已修）**
`18-GitHub上传指令包.md` 在描述"全库无明文口令"时，把口令本身写进了扫描报告表格 ——
文档成了全库唯一一处明文口令。典型"反讽式泄露"。已改为不写字面量（commit `9b9a884`）。

> ⚠️ **遗留**：该口令已进入 git 历史（`ac08668`）。仓库为 Private 风险可控，
> 但这是弱口令且已入历史，**建议换个新口令**（见第六节待办）。

**② `.idea/` 误入库 7 个文件（已修）**
首次提交把 PyCharm 配置（含本地绝对路径）一起提交了。已 `git rm --cached` 移除、
`.gitignore` 补 `.idea/` 与 `*.iml`（commit `7f992a4`）。

### 其它判定（可接受，转公开时需处理）

P02 的 `smoke_local.py` / `verify_llm_real.py` / `test_bootstrap.py` 等含本地测试假口令
（`LocalDev123!`、`Verify123!`、`secret-password`、`CloudPivot@2026`），
均为**演示项目的本地测试账号**，非生产凭据，Private 仓库下可接受。
**若将来转 Public，需改为环境变量或占位符。**

---

## 六、本次待办（P0）

- [x] 建 GitHub 仓库 `liyibo0410/yunshu-ai-portfolio` ✅ 已完成
- [x] **转 Private** ✅ 已完成（P1 已复验：未认证 API 返回 404）
- [ ] 把第三节指令粘给 Qoder 执行首传 ✅ 已完成（807 文件）
- [ ] **推送 P1 的两个修正 commit**（沙箱无 GitHub 凭据，需 Qoder 或你本地执行）：
      ```
      cd "D:\software\PycharmProjects\面试项目"
      git push
      git log --oneline -3        # 应见 7f992a4 / 9b9a884 / ac08668
      ```
- [ ] **（建议）更换服务器 SSH 口令** —— 原口令是弱口令且已进入 git 历史
      （Private 仓库风险可控，但换掉更稳妥；换完告诉我，我把新值记进本地凭据文档）
- [ ] 确认 push 成功后，把 commit hash 告诉 P1（我记进进度文档）

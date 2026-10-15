# GitHub Pages 静态版作品集 · 部署说明

本目录（`deploy/gh-pages/`）是作品集的**统一入口页**：`index.html` 现在是一个**纯跳转页**——打开即重定向到实机演示 `http://39.96.200.45:8070/`，不再停留中间页。部署目标地址：

> https://liyibo0410.github.io/yunshu-ai-portfolio/  →  立即跳转到  http://39.96.200.45:8070/

> 注意：实机演示依赖本机隧道常驻（看门狗 `CloudPivotTunnelWatchdog` 保活）。若电脑关机 / 隧道未起，跳转会失败——页面会显示一行兜底提示并给出「开源代码」链接。完整静态作品集内容已保留在 `gh-pages` 分支历史中，需要时可还原。

---

## 0. 仓库可见性（已验证 ✅）

Pages 站点上的「源码仓库」按钮全部指向 `github.com/liyibo0410/yunshu-ai-portfolio`，**若仓库是 Private，访客点了全是 404**。验证命令：

```bash
curl -s -o /dev/null -w "%{http_code}" https://github.com/liyibo0410/yunshu-ai-portfolio
```

- **200 = Public，无需处理**（2026-10-15 本机实测结果：**200**，仓库已是 Public）
- 404 = Private，需要仓库所有者在 **Settings → General → Danger Zone → Change repository visibility → Public** 手动改为 Public

---

## 1. 启用 Pages（仓库所有者操作）

GitHub 仓库页面 → **Settings** → 左侧 **Pages** → **Build and deployment** 下：

- **Source** 选 `Deploy from a branch`
- 分支与目录按下面两种方式二选一
- 点 Save，等 1–3 分钟生效；之后每次 push 对应分支会自动重新部署

---

## 2. 两种部署方式（命令供参考，push 一律由用户本人执行）

### 方式 A（推荐）：`gh-pages` 分支，只含静态页，仓库其余内容不受影响

用 git 内置的 subtree，不需要额外工具：

```bash
# 在仓库根目录执行（先确认 deploy/gh-pages/index.html 已提交到当前分支）
git subtree push --prefix deploy/gh-pages origin gh-pages
```

然后在 Settings → Pages 里选：**Branch: `gh-pages` / `(root)`**。

> 若 `git subtree push` 报分支为空或不存在的错，先本地建空分支再推：
> ```bash
> git checkout --orphan gh-pages-tmp
> git rm -rf . --quiet
> cp ../deploy/gh-pages/index.html .        # 路径按实际调整
> git add index.html && git commit -m "pages: static portfolio"
> git push origin gh-pages-tmp:gh-pages
> git checkout main && git branch -D gh-pages-tmp
> ```

### 方式 B：`main` 分支的 `docs/` 目录

把静态页放进仓库根的 `docs/` 文件夹：

```bash
mkdir -p docs
cp deploy/gh-pages/index.html docs/index.html
# 本 README 不必部署，可不复制
git add docs/index.html
git commit -m "docs: GitHub Pages 静态作品集"
git push origin main
```

然后在 Settings → Pages 里选：**Branch: `main` / `docs`**。

---

## 3. 部署后自检

1. 打开 https://liyibo0410.github.io/yunshu-ai-portfolio/ 会**立即跳转到** `http://39.96.200.45:8070/`（实机演示外壳）
2. 若演示服务器在线，跳转后能看到微前端外壳与十张模块卡
3. 若演示服务器离线，页面显示一行兜底提示，含「进入演示」「开源代码」两个链接（均非 404）

## 4. 内容事实来源

页面上的指标与 Mock 边界全部取自仓库内证据，未编造：`shell/index.html` 首屏模块卡（MODULE_INFO）、`docs/adr/`、`_evidence/INDEX.md`、`.workbuddy/memory/2026-10-14.md` 与 `2026-10-15.md`。修改页面内容时请保持同样的诚实口径：没测过的写「未测」，mock 的写「mock」。

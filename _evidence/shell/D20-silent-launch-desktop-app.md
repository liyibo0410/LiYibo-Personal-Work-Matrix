# D20 · 静默一键启动 + 桌面应用程序（2026-10-14 上午）

## 现象

`start-all.bat` 双击后桌面弹出十几个黑色终端窗口（一个服务一个），关掉即断；
统一入口本身反而被埋在窗口堆里。要求：静默一键启动 + 桌面上一个应用程序图标。

## 根因（三条，逐条实测）

### 1 · `DETACHED_PROCESS` 在 Win11「默认终端」接管下照样弹窗口

`_tools/supervisor.py` 的 `spawn()` 一直用 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`，
代码注释写的是「不继承本进程控制台」。在本机（Win11 24H2 + 默认终端应用 = Windows Terminal）
这个假设**不成立**：控制台子进程仍会被默认终端接管，每个服务开一个可见窗口。

探针 `_tmp_issue/window_probe.py` 复用 `supervisor.spawn()` 真实代码路径起服务，
每 300ms `EnumWindows` 比对可见顶层窗口，实测 **10 个服务 → 11 个新窗口**：

| 抓到的窗口 class | 宿主进程 | 标题（即服务命令行） |
|---|---|---|
| `CASCADIA_HOSTING_WINDOW_CLASS` | `WindowsTerminal.exe`（单一 pid 36512） | `uv run python app/main.py` ×4、`...\python.exe run.py`、`...\python.exe -m uvicorn ...`、`...\python.exe scripts/run_local_dev.py`、`C:\WINDOWS\system32\cmd.exe`（npm 那条）等 |

对照 A/B（`_evidence/shell/D20-flags-ab-test.log`）：**同一条命令行只换标志位** ——

```
旧 DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP: 新增控制台窗口 1
新 CREATE_NO_WINDOW |CREATE_NEW_PROCESS_GROUP: 新增控制台窗口 0
```

**修复**：`spawn()` 改用 `CREATE_NO_WINDOW`（走隐藏 conhost，不参与默认终端接管）。
子进程仍有独立控制台，父脚本退出后服务照活，`DETACHED_PROCESS` 原本要的那条性质没丢。

### 2 · 顺手挖出一个一直存在的真 bug：P01 商城中台在「无控制台」路径下必崩

改完标志位，`p01-commerce`（18081）仍不起。日志 `_runtime/logs/p01-commerce.log`：

```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680' in position 0
```

根因：`projects/p01-ai-customer-service/external/ecommerce-service-backend/main.py:14`
用 `print("🚀 ...")`，而 stdout 被重定向成日志文件后按 **GBK** 编码 → 进程直接退出。
只要服务带着控制台窗口跑（老路径）就不会暴露，所以此前 15 端口探活从未抓到它 ——
**这条不是静默启动引入的，是它把原有的坑照出来了**。

**修复**：`spawn()` 给子进程环境加 `PYTHONIOENCODING=utf-8`（只作用于 stdio，
不改文件 IO 的默认编码，避免连带影响各模块读中文文本文件）。

### 3 · 桌面入口是 pythonw，服务解释器不能跟着变成 pythonw

`resolve_python()` 回落到 `sys.executable`，从桌面应用进来时它就是 `pythonw.exe`
（GUI 子系统，`CREATE_NO_WINDOW` 对它无效，崩溃也只留一个看不见的死进程）。
实测 shell 网关一度以 `pythonw serve.py` 运行。**修复**：归一化到同目录 `python.exe`。

## 新增入口

| 文件 | 作用 |
|---|---|
| `_tools/launcher.py` | 静默编排：`start` / `stop` / `status` / `open`。全程无窗口、无 `pause`，输出只落 `_runtime/logs/launcher.log`；门户端口就绪即开浏览器，其余服务后台继续就绪；命名互斥量 `CloudPivot_launcher` 防连点重复起服务；**只在服务没起来时**弹一个 MessageBox（选「是」直接打开日志目录） |
| `_tools/make_desktop_app.py` | 一次性生成桌面应用：`brand.json` 的 logo（data URL PNG）→ 多尺寸 `cloudpivot.ico`（16/24/32/48/64/128/256）→ 用系统自带 `csc.exe` 编 `_tools/dist/云枢智能.exe`（`/target:winexe`，41,984 字节，不引入任何运行时依赖）→ 在桌面写三个快捷方式 |
| 桌面 · `云枢智能 一键启动.lnk` | 双击 = 静默起 15 个服务 + 自动打开门户 |
| 桌面 · `云枢智能 停止服务.lnk` | 双击 = 静默停全部（含 `--takeover` 收占用端口的旧进程） |
| 桌面 · `云枢智能 服务状态.lnk` | 双击 = 弹窗显示 15 端口逐个 TCP 实测结果 |

exe 里烘焙了仓库绝对路径与 `pythonw.exe` 路径，并有「从 exe 自身位置往上回推」的兜底；
仓库搬家 / 换 Python 版本 / 换品牌 logo 后重跑 `python -X utf8 _tools\make_desktop_app.py` 即可。

## 实测结果

双击桌面图标（`os.startfile` 等价路径），窗口监视跑满 170s
（`_evidence/shell/D20-window-watch-silent-start.log`）：

```
baseline=9 windows @ 08:47:52
合计新窗口 6，其中控制台类 0
```

那 6 个是浏览器页面与系统弹窗，**没有一个控制台窗口**。

时间线取自 `_evidence/shell/D20-launcher.log`：

| 时刻 | 事件 |
|---|---|
| 08:48:07 | 15 个服务逐个 `[启动]`（spawn 阶段无阻塞） |
| 08:48:09 | 门户 8800 就绪 → 自动开浏览器（**+2s**） |
| 08:48:19 | `全部 15 个服务在线`（**+12s**，依赖已装的暖启动） |
| 08:52:02 → 08:52:10 | 「停止服务」图标：`已发送停止指令` → `全部端口已释放`（**8s**），复测 0/15 |
| 08:52:56 → 08:52:58 → 08:53:04 | 再点「一键启动」：门户就绪 **+2s** → `全部 15 个服务在线` **+8s** |
| 08:55 | `supervisor.py status` = **15/15 在线**（`_evidence/shell/D20-supervisor-status.log`） |

「服务状态」图标的弹窗链路也实测通过：抓到 `#32770` 弹窗、标题「云枢智能 · 服务状态」、
正文 20 行端口表（自动关闭，未留模态在屏）。`GET http://127.0.0.1:8800/` → **200**。

## 边界（别当成已经全好了）

- **`start-all.bat` 仍会开它自己那一个控制台窗口** —— 它就是给人看进度并 `pause` 的；
  要零窗口就用桌面图标或 `pythonw _tools\launcher.py`。修好标志位后，bat 也不再弹服务窗口了。
- **P01 自带的 `tools/dev_up.py` 仍用 `CREATE_NEW_CONSOLE`**（它的文档里写明「窗口即日志」，
  是模块级自测入口）；统一平台路径不经过它，本轮不动它的设计。
- 强杀 launcher 时**不要带 `/T`**：服务是它的子孙进程，`taskkill /PID <launcher> /T`
  会把 15 个服务一起带走（本轮踩过一次，随后用桌面图标静默恢复）。
- 桌面项是快捷方式 + 本地 exe，不是安装包；**没有公网入口**这条与本轮无关，仍是老问题（见 D12/D13）。
- 12s 就绪是暖启动数字（依赖已装、venv 已建）；首次冷启动要加 `uv sync` / `npm install` 的时间，本轮未测。

# 0002 · SERVICE_REGISTRY：端口与路由的唯一真源

- 状态：Accepted
- 日期：2026-10-12

## 背景

多模块互相调用（P02 取 P06 指标、P09 取 P01 会话）与外壳挂载都需要端口。早期端口散落在各模块代码与启动脚本里，改一个端口要翻多处，且出现过 P03 前端把后端端口写错（写成 8000，实为 8030）导致平台内不可用的真实故障。

## 决策

建立 `shared/config/services.json` 作为**端口的唯一真源**：每个服务一条记录，含 `api_port / web_port / route / api_prefix / layer / icon / status`。

- Python 侧：`cloudpivot_config` 提供 `api_url(id, path)` / `service_url(id)`，跨模块调用一律从这里解析端口。
- 前端侧：`build_js.py` 把 JSON 生成镜像 `services.js`（`window.CP_REGISTRY`），外壳据此解析挂载端口；也可运行时读 `/api/registry`。
- 改端口只改 `services.json`，再跑 `build_js.py` 重新生成前端镜像。
- 约定：模块可以硬编码**自己**的后端端口（如 P03 Vite proxy → 8030），但**禁止**硬编码**其他模块**端口。

## 后果

- (+) 端口漂移从「多处改」变成「一处改 + 一次再生成」；跨模块调用与挂载共享同一份地址。
- (+) `/api/registry` 让前端注册表与后端解析同源，避免镜像与真源长期不一致。
- (−) 存在一份**生成物**（`services.js`）需与 `services.json` 同步；忘跑 `build_js.py` 会让前端读到旧端口（已在注释与 ADR 中强调再生成步骤）。

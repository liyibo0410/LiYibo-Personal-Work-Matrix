# P01 AI电商客服系统

> 云枢智能（CloudPivot）平台 · L3 应用层模块
> 智能电商客服平台 -- 数字人 TTS x 领域知识问答 x 订单查询 x 闲聊分流 x 多轮对话

## 一句话定位

面向电商场景的智能客服后端系统，集成大模型对话、数字人语音合成、领域知识检索、订单商品查询等能力，支持智能分流（客服/闲聊/澄清）与流式响应。

## 源项目信息

| 项 | 值 |
|---|---|
| 源项目路径 | `D:\software\PycharmProjects\customer-service-backend\` |
| 改造方式 | 复制到 `projects/p01-ai-customer-service/` 后重构 |
| 源项目状态 | 原件未修改（遵守红线规则） |

## 技术栈

| 层 | 技术 |
|---|---|
| **后端框架** | Python 3.12 + FastAPI + Pydantic v2 + Uvicorn |
| **AI/LLM** | LangChain + init_chat_model（OpenAI 兼容协议，可切换任意厂商） |
| **语音合成** | Edge-TTS（数字人语音播报） + 魔珐星云（数字人驱动，可选） |
| **ORM** | SQLAlchemy 2.0（异步） |
| **数据库** | MySQL 8.x（Docker 容器，端口 3307） |
| **前端** | Vue 3 + Vite（端口 5173，代理后端 API） |
| **商城中台** | 自带 mock 电商后端（端口 18081，提供订单/商品数据） |
| **包管理** | uv（pyproject.toml + uv.lock） |

## 架构概览

```
用户浏览器 (:5173)
    |
    v  (Vite proxy)
FastAPI 后端 (:18082)
    |
    +-- api/           路由层: POST /api/chat, GET /api/chat/history, 数字人/TTS
    |
    +-- service/       业务编排层: DialogueService (加载状态->引擎推理->保存状态)
    |
    +-- engine/        对话引擎: DialogueEngine (调度中枢)
    |       |
    |       +-- plan/          意图规划: TurnPlanner(LLM) + TurnPlanValidator(防幻觉)
    |       +-- task/          任务轨道: TaskHandler + 流程引擎 (订单查询/退换货等)
    |       +-- knowledge/     知识轨道: 知识检索 + 精准问答
    |       +-- chitchat/      闲聊轨道: LLM 自由对话
    |       +-- clarify/       澄清模块: 追问话术生成
    |
    +-- domain/        领域模型: UserMessage/BotMessage/DialogueState/Session/Turn
    +-- repository/    数据仓储: DialogueStateRepository (MySQL 持久化)
    +-- infrastructure/ 基础设施: LLM 客户端 / 数据库连接池 / HTTP 客户端
    +-- prompts/       Prompt 模板 (Jinja2)
    +-- flow_config/   业务流程定义 (YAML)
    |
    v
MySQL (:3307)        商城中台 (:18081)
```

### 核心设计

- **三轨道分流**：用户消息经 LLM 意图识别后分流到 task（任务执行）/ knowledge（知识问答）/ chitchat（闲聊）三条轨道
- **防幻觉校验**：LLM 输出的 TurnPlan 必须经过 TurnPlanValidator 校验，不合法则走澄清而非执行
- **会话管理**：Session -> Turn 两级结构，1 小时超时自动关闭旧会话开新会话
- **对象消息**：前端点击订单/商品卡片会作为 FocusedObject 发送，引擎自动映射为流程槽位填充
- **依赖注入**：Engine 的各"专员"均由外部构造后注入，便于测试替换

## 快速启动

### 前置条件

- Python 3.12+
- uv（包管理器）
- Node.js 18+ / npm
- Docker Desktop（用于 MySQL 容器）

### 一键启动（推荐）

```bash
# 双击 start-dev.bat 或命令行执行：
start-dev.bat

# 等价于：
uv run python tools/dev_up.py
```

该脚本按顺序拉起：MySQL(3307) -> 商城中台(18081) -> AI客服后端(18082) -> 前端dev(5173)

### 手动启动

```bash
# 1. 安装后端依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY 等配置

# 3. 启动 MySQL（Docker）
docker compose -f external/docker/docker-compose.yml up -d mysql

# 4. 建库建表（首次）
uv run python tools/dev_up.py --init-db

# 5. 启动后端
python main.py

# 6. 安装并启动前端
cd external/customer-service-frontend
npm install
npm run dev
```

### 访问

- 前端页面：http://localhost:5173
- 后端 API 文档：http://localhost:18082/docs
- 后端健康检查：http://localhost:18082/health

## API 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat` | 发送消息（文本或对象卡片），返回机器人回复 |
| GET | `/api/chat/history?sender_id=<id>` | 获取用户历史对话 |
| GET | `/api/digital-human/credentials` | 获取数字人凭证 |
| POST | `/api/chat/tts` | 文本转语音 |
| GET | `/health` | 存活探针 |

## 功能清单

| 功能 | 状态 | 说明 |
|---|---|---|
| 多轮对话 | 已实现 | 上下文记忆、会话超时自动换新 |
| 意图识别与分流 | 已实现 | LLM 规划 -> 防幻觉校验 -> 三轨道分流 |
| 知识问答 | 已实现 | 领域知识库检索，精准回答商品/售后问题 |
| 任务流程（订单查询等） | 已实现 | YAML 定义流程，槽位收集 + 命令执行 |
| 对象卡片交互 | 已实现 | 点击订单/商品卡片自动填充流程槽位 |
| 闲聊 | 已实现 | LLM 自由对话 |
| 澄清追问 | 已实现 | 9 种原因码 -> 自然语言追问 |
| 数字人 TTS | 已实现 | Edge-TTS 语音合成 + 魔珐星云数字人（可选） |
| 对话历史 | 已实现 | MySQL 持久化，按 session 展开 |
| 商城中台对接 | 已实现 | 订单/商品数据查询（自带 mock 后端） |
| LLM 调用治理 | 已实现 | 超时/重试/降级，避免模型侧抖动直接 500 |

## 端口约定

| 端口 | 服务 |
|---|---|
| 3307 | MySQL（Docker 容器） |
| 18081 | 商城中台（mock 电商后端） |
| 18082 | AI 客服后端（FastAPI） |
| 5173 | 前端开发服务器（Vite） |

## 项目结构

```
p01-ai-customer-service/
|-- main.py                 # 服务启动入口
|-- pyproject.toml          # uv 包管理
|-- start.bat               # 一键启动（仅后端）
|-- start-dev.bat           # 一键启动（全套服务）
|-- conf/                   # 配置层（pydantic-settings 读 .env）
|-- api/                    # API 路由层
|   |-- app.py              #   FastAPI 应用 + lifespan
|   |-- routers/            #   路由定义
|   +-- schemas.py          #   请求/响应模型
|-- service/                # 业务编排层
|-- engine/                 # 对话引擎（调度中枢）
|-- plan/                   # 意图规划 + 防幻觉校验
|-- task/                   # 任务轨道（流程引擎 + 命令执行）
|-- knowledge/              # 知识轨道（检索 + 问答）
|-- chitchat/               # 闲聊轨道
|-- clarify/                # 澄清模块（追问话术）
|-- domain/                 # 领域模型
|-- models/                 # ORM 模型
|-- repository/             # 数据仓储
|-- infrastructure/         # 基础设施（LLM/DB/HTTP）
|-- prompts/                # Prompt 模板（Jinja2）
|-- flow_config/            # 业务流程定义（YAML）
|-- digital_human/          # 数字人 TTS
|-- external/               # 外部依赖
|   |-- customer-service-frontend/  # Vue 3 前端
|   |-- ecommerce-service-backend/  # 商城中台（mock）
|   +-- docker/             # Docker Compose（MySQL）
|-- tools/                  # 开发工具（一键启动器等）
+-- test/                   # 测试
```

## 已知限制与 Mock 边界

- **LLM 调用**：需要真实 API Key（配置在 .env 的 LLM_API_KEY），支持 OpenAI 兼容协议的任意厂商
- **商城中台**：`external/ecommerce-service-backend/` 是课程配套的 mock 后端，数据为样例数据，非真实业务系统
- **数字人**：魔珐星云需要单独申请 App ID / App Secret，未配置时数字人接口返回"未配置"，不影响核心对话功能
- **语音播报**：Edge-TTS 为微软免费 TTS 服务，需联网调用

## License

MIT

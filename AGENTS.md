# AGENTS.md · 面试作品集平台

> 本文件供 Qoder / Claude Code / CodeBuddy 等 AI 编程工具自动加载。
> 详细规范见 `.qoder/rules/`，架构总纲见 `00-总纲/00-总纲提示词.md`。

## 这是什么

一套面向 **AI 应用开发 / AI-FDE 岗位** 的作品集工程：由**十个 AI 能力模块**组成一套统一的「AI 电商运营中台」。

**核心叙事**：底层数据中台统一口径 → 模型层沉淀微调能力 → 能力层提供 RAG / 研究 / 素材 / 切片 → 应用层组装成客服 / 运营 / 合同 / 考核四条业务线，并通过数据回流形成闭环。

## 公司设定（虚构，用于业务建模）

- 名称：**云枢智能（CloudPivot）** —— 面向品牌电商与 MCN 的 AI 原生运营服务商
- 客户：年 GMV 千万至十亿级的品牌方、代运营公司、直播机构
- 设定规模：服务 200+ 店铺，日均会话 50 万条 → 因此**多租户 / 多店铺 / 高并发 / 数据合规**是每个模块都要体现的设计约束

## 十个模块

| 层 | 编号 | 模块 | 目录 | 来源 |
|---|---|---|---|---|
| L3 应用 | P01 | AI 电商客服 | `projects/p01-ai-customer-service` | 改造 customer-service-backend |
| L3 应用 | P02 | 电商运营助手 ★旗舰 | `projects/p02-ecommerce-ops-assistant` | 改造 ecommerce-operation-assistant |
| L2 能力 | P03 | Deep Research 问数 | `projects/p03-deep-research` | 改造 deep_agent_search |
| L2 能力 | P04 | RAG 知识库 | `projects/p04-rag-knowledge-base` | 改造 knowledge_base |
| L3 应用 | P05 | 合同审批系统 | `projects/p05-contract-review` | 改造 合同审批系统-李奕波 |
| L0 数据 | P06 | 数据中台 | `projects/p06-data-platform` | 新建 |
| L2 能力 | P07 | AI 素材中心 | `projects/p07-ai-asset-center` | 新建 |
| L2 能力 | P08 | 直播切片 | `projects/p08-live-clip` | 新建 |
| L3 应用 | P09 | AI 销售考核 | `projects/p09-ai-sales-assessment` | 新建 |
| L1 模型 | P10 | 模型微调平台 | `projects/p10-model-finetune` | 新建 |

## 四条不可动摇的规矩

1. **真跑通 > 好看**：声称完成的功能必须有真实证据（启动日志 / 接口返回 / 截图 / 测试输出），落到 `_evidence/`。跑不通就写"未跑通 + 原因"。
2. **不造假**：不编造数据、指标、性能数字。允许本地 mock，但必须在 UI 与 README **双处标注** mock 边界。
3. **不动原件**：`D:\software\PycharmProjects\` 下的**原始项目禁止删除或覆盖**，改造一律复制到本项目 `projects/` 后重构。
4. **高风险先问**：删除 / 覆盖 / 批量重命名 / 对外发布，必须先红色警告 → 列受影响路径 → 等确认。

## 环境要点

- Python 包管理**强制 uv**（`pyproject.toml` + `uv.lock`），禁用裸 `pip install`
- 模型调用一律走 `shared/llm-gateway`，配置从根目录 `.env` 读取，**禁止硬编码 Key**
- 本机：Windows + RTX 4060 8GB + 16GB 内存 + **磁盘紧张**（D 盘仅剩 ~64G，重物走 E 盘）
- Docker 可用；Node 22 可用；ffmpeg 9.0 可用

## 当前阶段

Phase 0（项目体检）已完成，见 `00-总纲/05-项目体检报告.md`。
下一步：按 `00-总纲/06-工具链与分工方案.md` 的分工执行。

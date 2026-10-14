/* 自动生成，请勿手改 —— 真源是 shared/config/services.json，改端口后重跑 build_js.py。 */
window.CP_REGISTRY = {
  "version": "1.0",
  "host": "127.0.0.1",
  "gateway": {
    "web_port": 8800
  },
  "layers": {
    "L3": "应用层",
    "L2": "能力层",
    "L1": "模型层",
    "L0": "数据层"
  },
  "services": {
    "p01": {
      "name": "AI 电商客服",
      "short": "P01 AI客服",
      "layer": "L3",
      "route": "customer-service",
      "icon": "chat",
      "api_port": 18082,
      "web_port": 5173,
      "commerce_port": 18081,
      "api_prefix": "/api",
      "status": "ready",
      "desc": "意图识别 + 知识检索 + 负面情绪自动建单转人工"
    },
    "p02": {
      "name": "电商运营助手",
      "short": "P02 运营助手",
      "layer": "L3",
      "route": "ecommerce-ops",
      "icon": "chart",
      "api_port": 8000,
      "web_port": 3001,
      "api_prefix": "/api/v1",
      "status": "flagship",
      "desc": "旗舰模块 · 文案生成 + 合规检测 + 广告实验 + 四角色 RBAC"
    },
    "p03": {
      "name": "NL2SQL 问数",
      "short": "P03 问数",
      "layer": "L2",
      "route": "research",
      "icon": "search",
      "api_port": 8030,
      "web_port": 5174,
      "api_prefix": "/api",
      "status": "ready",
      "desc": "自然语言 → SQL → 图表 → 溯源报告，含只读护栏与拒答"
    },
    "p04": {
      "name": "RAG 知识库",
      "short": "P04 知识库",
      "layer": "L2",
      "route": "knowledge",
      "icon": "book",
      "api_port": 8041,
      "web_port": 8041,
      "api_prefix": "",
      "status": "ready",
      "desc": "文档入库 → 检索问答带引用 → 召回/精确/拒答/忠实度评测"
    },
    "p05": {
      "name": "合同审批系统",
      "short": "P05 合同审批",
      "layer": "L3",
      "route": "contract",
      "icon": "doc",
      "api_port": 8770,
      "web_port": 8770,
      "api_prefix": "/api",
      "status": "ready",
      "desc": "衡鉴 · 零依赖确定性风险审查引擎 + 审批回写"
    },
    "p06": {
      "name": "数据中台",
      "short": "P06 数据中台",
      "layer": "L0",
      "route": "data-platform",
      "icon": "database",
      "api_port": 8060,
      "web_port": 8060,
      "api_prefix": "/api/v1",
      "status": "ready",
      "desc": "接入 / 数仓分层 / 指标口径 / 血缘 / 质量校验"
    },
    "p07": {
      "name": "AI 素材中心",
      "short": "P07 素材中心",
      "layer": "L2",
      "route": "asset-center",
      "icon": "image",
      "api_port": 8070,
      "web_port": 8070,
      "api_prefix": "/api/v1",
      "status": "ready",
      "desc": "素材上传 → 打标 → 以文搜图 → 投放效果关联"
    },
    "p08": {
      "name": "直播切片",
      "short": "P08 直播切片",
      "layer": "L2",
      "route": "live-clip",
      "icon": "video",
      "api_port": 8080,
      "web_port": 8080,
      "api_prefix": "/api/v1",
      "status": "ready",
      "desc": "样例视频端到端出片 + 可解释打点 + 批量队列"
    },
    "p09": {
      "name": "AI 销售考核",
      "short": "P09 销售考核",
      "layer": "L3",
      "route": "sales-assessment",
      "icon": "trophy",
      "api_port": 8090,
      "web_port": 8090,
      "api_prefix": "/api/v1",
      "status": "ready",
      "desc": "导入会话 → 自动评分 → 排行榜与个人报告，规则+LLM 可解释"
    },
    "p10": {
      "name": "模型微调平台",
      "short": "P10 微调平台",
      "layer": "L1",
      "route": "finetune",
      "icon": "brain",
      "api_port": 8101,
      "web_port": 8101,
      "api_prefix": "/api/v1",
      "status": "ready",
      "desc": "数据 → 训练 → 评测 → 模型注册表（训练与部署均为模拟，无可调用端点）"
    }
  }
};

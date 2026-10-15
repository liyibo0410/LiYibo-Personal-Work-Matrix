# P09 → P10 低分样本回流验证（考核 → 微调）

时间：2026-10-14 23:2x

## 架构规范落实
- P10 侧新增 `app/p09_client.py`，**只用标准库 `urllib`**（P10 刻意保持零第三方运行时依赖，不为一次跨模块 GET 引入 httpx）。
- 端口从 SERVICE_REGISTRY 解析：读仓库根 `shared/config/services.json` 的 `p09.api_port`（=8090），
  **不硬编码**；支持 `CP_P09_EXPORT_URL` 显式覆盖（降级演练用）；最后才退回环境变量。
- P09 侧新增 `GET /api/v1/export/low-score?threshold=&limit=`：只导出「已评分且 `overall < threshold`」的会话，
  最差优先排序，并随样本给出评分口径（`scoring_engine=rule-based(mock-llm)`）。

## 1. 正常路径（SERVICE_REGISTRY → 8090 活实例）
```
p09 export: 200 exported=22 low_total=22 engine=rule-based(mock-llm)
p10 from-p09: 200 ok=True source=p09-live
dataset: ds-101 P09 低分会话回流（<100 分） sample_count=22 provenance=p09-export measured=['sample_count']
```
→ P10 把 P09 的低分会话登记为一个可训练数据集，`sample_count` 取**拉取到的真实条数**（写入 `measured_fields`），
不是估值。原始响应：`cross-module-p09-20261014.json`。

## 2. 降级路径（`CP_P09_EXPORT_URL` 指向死端口 59999，实测）
```
{"ok": false, "degraded": true, "source": "unavailable",
 "error": "P09 销售考核不可达：<urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>"}
```
→ 路由随后返回 `ok=false/degraded=true/dataset=null` 且**不创建任何数据集**（降级不伪造）。

## 结论
- 正常路径：P09 质检低分样本 → P10 微调数据集，**真实 HTTP**，闭环再补一环
  （叙事：销售考核 → 低分样本回流微调）。
- 降级路径：不伪造样本、不建空壳数据集。
- 测试：`_evidence/p09-ai-sales-assessment/pytest-20261014-export-lowscore.log`（P09 **55 passed**，+4）、
  `_evidence/p10-model-finetune/pytest-20261014-from-p09.log`（P10 **35 passed**，+4）。
- **未做**：P10 前端「从 P09 拉取」按钮未加（本轮到接口层）；P10→P01/P02 的「新模型回写」仍未接线；
  P09 评分为规则引擎（mock LLM），回流样本的引用须保留该口径。
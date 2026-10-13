# P05 合同审批（衡鉴）· 证据索引

> 本目录登记 P05 模块的真实执行证据。规则见 `.qoder/rules/04-验收门禁.md`：
> 声称完成的功能必须有一次真实执行的证据，跑不通就写「未跑通 + 原因」。

## pytest 单元 / 端到端测试

- **证据文件**：`pytest-20261013.log`
- **执行命令**：`uv run python -m pytest tests -v -o addopts=""`
- **执行时间**：2026-10-13
- **环境**：Python 3.11.15 / pytest 9.1.1 / Windows（`.venv` 由 `uv sync` 创建，仅装 pytest，被测代码零第三方依赖）
- **结果**：**46 passed in 1.15s**（0 失败 / 0 跳过）

### 这条证据证明了哪些门禁

| 测试文件 | 覆盖能力 | 对应验收门禁 |
|---|---|---|
| `tests/test_e2e_and_store.py::test_gate_identifies_breach_asymmetry` | 解析真实样本 `samples/03_大额销售合同_违约责任不对等.docx` → 跑 sales 规则库 → **SA-H-001「违约责任不对等」被识别为高风险**，命中带原文证据 + 页码 + 字符坐标 + 两侧（本方/对方）证据 | 「风险用例被正确识别（如'违约责任不对等'）」 |
| `test_parse_gate_sample_docx` | DOCX 由标准库 zipfile+xml 直接解析出段落树，每段带 page/index/char_start/char_end 可溯源坐标 | 「双向可溯源定位」 |
| `test_all_samples_parse_without_crash` | samples/ 下 8 份文档（DOCX/PDF/加密/扫描）全部安全返回，非加密 DOCX 出文本 | 解析健壮性 |
| `test_encrypted_or_scanned_goes_manual` | 加密 PDF / 扫描件走 `need_manual` 降级，不伪装成功 | 解析降级路径（诚实标注） |
| `test_gate_conclusion_not_pass` | 命中高风险后结论为「需整改/建议拒绝」，不会是「通过」 | 结论判定 |
| `test_store_roundtrip` / `dedupe_by_sha` / `update_whitelist_and_audit` | SQLite 持久层：建案件→存文档→写命中→总风险取最高→指纹去重→字段白名单→审计留痕（用 tmp_path 临时库，不碰 data/review.db） | 状态落库 |
| `tests/test_review.py`（36 条） | 引擎纯函数：despace 坐标无损映射、_cmp 数值比较、classify_clause、split_clauses、clause_coverage、extract_metadata（主体/信用代码/金额/币种/标题）、decide_conclusion、build_suggestion；run_rules 五种匹配模式 keyword/absence/numeric/**asymmetry**/regex，非法正则进 diag 不静默失效 | 规则引擎正确性 |

## 未测量 / 未覆盖（诚实边界）

- **二阶段 LLM 语义复核**（`app/llm.py` 的 `review_hits`）未纳入单测：`config/app.json` 默认 `llm.enabled=false`，走 mock 降级；本套件只验证「规则全量召回」这条确定性主路径，不测 LLM 判定质量。
- **HTTP 服务层**（`app/server.py` ThreadingHTTPServer）、**审批回写**（`app/writeback.py`）、**通知**（`app/notify.py`）、**队列/调度**（`app/queue.py`/`scheduler.py`）未做接口级测试；本次只覆盖审查引擎 + 解析 + 持久层核心链路。
- **性能指标**（并发吞吐、P95）未测量。
- OCR（`app/ocr_win.py`）依赖 Windows WinRT，扫描件样本能否出文本取决于本机 OCR 可用性，测试对扫描件仅断言「不崩溃 + 失败时标 need_manual」，不硬断言识别成功。

## 相关文档

- 模块 README：`projects/p05-contract-review/README.md`
- 项目自带全量自检脚本（非 pytest）：`projects/p05-contract-review/selftest.py`

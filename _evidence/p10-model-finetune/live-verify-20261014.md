# P10 去编造指标 · 真实运行核验（2026-10-14 00:0x）

改动目的：P10 的接口里原先存在**没有测量来源的数字**（写死的 P50/P95 延迟、随机数据集统计、
以及一个指向不存在服务的 `endpoint_url` 还标成 healthy）。UI 黄条只能对网页有效，
curl 接口的人拿到的仍是假数字 —— 违反红线 2「禁止编造」与红线 3「禁止把 mock 冒充真实」。

服务已用 `_tools/supervisor.py restart p10 --takeover` 重启，下列输出全部来自**运行中的 8101 端口**，
不是测试桩。

## 1. `GET /api/v1/models` —— 不再存在假端点

```json
[
 {"id":"model-001","status":"deployed_simulated","endpoint_url":null,"endpoint_status":"simulated","simulated":true},
 {"id":"model-002","status":"registered","endpoint_url":null,"endpoint_status":null,"simulated":true},
 {"id":"model-003","status":"registered","endpoint_url":null,"endpoint_status":null,"simulated":true}
]
```

改前（历史行为，见 `app/main.py` 原 `_m1` 定义）：
`status="deployed"` + `endpoint_url="http://127.0.0.1:8101/v1"` + `endpoint_status="healthy"`。
8101 是 P10 自己的 FastAPI 端口，`/v1/chat/completions` 返回 404 —— 那是把不存在的服务标成健康。

## 2. `GET /api/v1/evaluations` —— 延迟改为未测量

```
eval-001        response_latency_p95_ms=None  未测量：无真实推理服务，无法产生延迟            simulated=True
eval-002        response_latency_p95_ms=None  未测量：没有真实推理服务，无法产生延迟            simulated=True
eval-baseline   response_latency_p95_ms=None  未测量：基座模型同样没有在本模块起服务            simulated=True
```

改前：`details.response_latency_p95_ms` 分别是写死的 `890 / 1120 / 750`，`p50` 是 `320 / 410 / 280`。

## 3. `GET /api/v1/stats`

```json
{"datasets":3,"training_runs":2,"completed_runs":2,"model_versions":3,
 "deployed_models":1,"deployed_simulated_models":1,"real_served_models":0,
 "total_samples":45700,"avg_accuracy":0.8367,"mock_mode":true,
 "metrics_provenance":"total_samples / avg_accuracy 是由预置演示数据算出来的聚合值，其中模型 accuracy 是模拟评分、未上传数据集的样本数是预置常量，均非实测"}
```

## 4. 数据集统计改为真实测量（回归测试覆盖）

`POST /api/v1/datasets` 上传 5 行 JSONL（含 2 行完全重复、3 种 label）后：
`file_size_bytes` = 真实字节数、`sample_count` = 5、`duplicates_removed` = 2、
`label_distribution` = `{退货申请:0.6, 咨询:0.2, 投诉:0.2}`（真解析出来的），
`avg_tokens` / `token_histogram` = `null`（没接 tokenizer 就不给数），
`char_length_percentiles` = 真实字符长度分位。
预置演示数据集则统一带 `provenance="seed_demo"`，UI 里数字后加 `*` 并给图例。
改前这些统计全部来自 `random.randint(5_000_000, 50_000_000)` 等随机数，
且标签分布/Token 分位是写死的常量（注释还写着「分布占比数值保持真实口径」）。

## 5. 测试

`pytest-20261014.log`：**28 passed**（原 26 条 + 2 条新增防回归：
`test_create_dataset_measures_the_uploaded_file_for_real`、
`test_deploy_model_does_not_fabricate_an_endpoint`、`test_stats_reports_no_real_served_model`；
其中 `test_create_dataset` 由「无文件也算 valid」改为断言 `pending`）。

## 6. 截图（Edge headless，绝对路径，真实渲染）

- `2026-10-14_评测对比_模拟声明.png` —— 评测页顶部新增「本页所有分数都是模拟评测值…不能当成微调带来 X 提升的证据」，
  对比表列头改为「变化（模拟）」
- `2026-10-14_模型仓库_无假端点.png` —— 模型卡显示「服务地址：无（仅登记了模拟部署状态，没有推理服务在运行，
  不存在可调用的 OpenAI 兼容端点）」，状态徽标为「模拟部署（无推理服务）」

顺带补的能力：`web/index.html` 支持 `#evaluation` / `#models` 这类页签深链
（外壳挂载、无头截图取证、分享具体视图都需要它，原先刷新必回总览）。

## 仍未满足的门禁（不要当成已完成）

`.qoder/rules/04-验收门禁.md` P10 行要求：真实训练跑完（哪怕 50 step）+ loss 曲线截图 +
微调前后评测对比 + 微调后模型 OpenAI 兼容接口 curl 调通。**四项全部未满足**，
本模块是「流程演示 + 口径诚实」，不是可交付微调平台。
可行的一次本地训练方案见 `00-总纲/07-P10微调算力方案.md`（RTX 4060 8GB + Qwen2.5-0.5B LoRA），尚未执行。
